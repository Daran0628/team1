import re
import subprocess
from datetime import datetime, timezone

from extensions import db
from domain.model.Vdi import Vdi, VdiSnapshot
from core.response.ErrorStatus import ErrorStatus


class VdiException(Exception):
    def __init__(self, error_status: ErrorStatus, detail: str = ""):
        self.error_status = error_status
        self.detail = detail


# Docker 리포지토리 이름 규칙: 소문자 영숫자 + '.' '_' '-' 구분자만 허용 (공백/대문자/한글/특수문자 불가)
_SNAPSHOT_NAME_RE = re.compile(r'^[a-z0-9]([a-z0-9._-]*[a-z0-9])?$')


def _docker(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ['docker', *args],
        capture_output=True, text=True, timeout=30,
    )


# ── CRUD ──────────────────────────────────────────────────────

def create_vdi(container_name: str, image: str, member_id: str) -> dict:
    if Vdi.query.filter_by(container_name=container_name).first():
        raise VdiException(ErrorStatus.VDI_ALREADY_EXISTS)
    if Vdi.query.filter_by(assigned_to=member_id).first():
        raise VdiException(ErrorStatus.VDI_MEMBER_ALREADY_HAS_VDI)

    result = _docker('run', '-dt', '--name', container_name, image)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_CREATE_FAILED, result.stderr.strip())

    vdi = Vdi(container_name=container_name, image=image, status='RUNNING', assigned_to=member_id)
    db.session.add(vdi)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        _docker('rm', '-f', container_name)
        raise VdiException(ErrorStatus.VDI_CREATE_FAILED, 'DB commit failed')
    return _to_dict(vdi)


def list_vdi(member_id: str | None = None) -> list[dict]:
    q = Vdi.query
    if member_id:
        q = q.filter_by(assigned_to=member_id)
    vdis = q.order_by(Vdi.created_at.desc()).all()
    for v in vdis:
        _sync_status(v)
    return [_to_dict(v) for v in vdis]


def get_vdi(vdi_id: str) -> dict:
    vdi = Vdi.query.get(vdi_id)
    if not vdi:
        raise VdiException(ErrorStatus.VDI_NOT_FOUND)
    _sync_status(vdi)
    return _to_dict(vdi)


def start_vdi(vdi_id: str) -> dict:
    vdi = _get_or_404(vdi_id)
    result = _docker('start', vdi.container_name)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())
    vdi.status = 'RUNNING'
    vdi.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _to_dict(vdi)


def stop_vdi(vdi_id: str) -> dict:
    vdi = _get_or_404(vdi_id)
    result = _docker('stop', vdi.container_name)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())
    vdi.status = 'STOPPED'
    vdi.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _to_dict(vdi)


def reboot_vdi(vdi_id: str) -> dict:
    vdi = _get_or_404(vdi_id)
    result = _docker('restart', vdi.container_name)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())
    vdi.status = 'RUNNING'
    vdi.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _to_dict(vdi)


def delete_vdi(vdi_id: str) -> None:
    vdi = _get_or_404(vdi_id)
    _docker('stop', vdi.container_name)
    result = _docker('rm', '-f', vdi.container_name)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())
    db.session.delete(vdi)
    db.session.commit()


# ── 스냅샷 ────────────────────────────────────────────────────

def create_snapshot(vdi_id: str, snapshot_name: str, member_id: str) -> dict:
    """VDI 컨테이너의 스냅샷(Docker 이미지)을 생성한다.
    snapshot_name은 Docker 이미지 태그에 그대로 쓰이므로 리포지토리 이름 규칙을 따라야 한다."""
    if not _SNAPSHOT_NAME_RE.match(snapshot_name):
        raise VdiException(ErrorStatus.VDI_INVALID_SNAPSHOT_NAME)

    vdi = _get_or_404(vdi_id)
    image_tag = f"{vdi.container_name}-snap-{snapshot_name}:latest"
    result = _docker('commit', vdi.container_name, image_tag)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())

    snap = VdiSnapshot(
        vdi_id=vdi_id,
        snapshot_name=snapshot_name,
        image_tag=image_tag,
        created_by=member_id,
    )
    db.session.add(snap)
    db.session.commit()
    return _snap_to_dict(snap)


def list_snapshots(vdi_id: str) -> list[dict]:
    """VDI의 스냅샷 목록을 최신순으로 반환한다."""
    _get_or_404(vdi_id)
    snaps = VdiSnapshot.query.filter_by(vdi_id=vdi_id).order_by(VdiSnapshot.created_at.desc()).all()
    return [_snap_to_dict(s) for s in snaps]


def create_vdi_from_snapshot(snapshot_id: str, container_name: str, member_id: str) -> dict:
    """스냅샷 이미지로 새로운 VDI를 생성한다. 기존 VDI는 그대로 유지된다."""
    snap = VdiSnapshot.query.get(snapshot_id)
    if not snap:
        raise VdiException(ErrorStatus.VDI_SNAPSHOT_NOT_FOUND)
    return create_vdi(container_name, snap.image_tag, member_id)


def restore_vdi_from_snapshot(vdi_id: str, snapshot_id: str) -> dict:
    """기존 VDI 컨테이너를 지정한 스냅샷 시점으로 되돌린다 (컨테이너 재생성, vdi_id 유지)."""
    vdi = _get_or_404(vdi_id)
    snap = VdiSnapshot.query.get(snapshot_id)
    if not snap or snap.vdi_id != vdi_id:
        raise VdiException(ErrorStatus.VDI_SNAPSHOT_NOT_FOUND)

    _docker('stop', vdi.container_name)
    result = _docker('rm', '-f', vdi.container_name)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())

    result = _docker('run', '-dt', '--name', vdi.container_name, snap.image_tag)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_OPERATION_FAILED, result.stderr.strip())

    vdi.image = snap.image_tag
    vdi.status = 'RUNNING'
    vdi.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return _to_dict(vdi)


# ── 내부 헬퍼 ─────────────────────────────────────────────────

def _get_or_404(vdi_id: str) -> Vdi:
    vdi = Vdi.query.get(vdi_id)
    if not vdi:
        raise VdiException(ErrorStatus.VDI_NOT_FOUND)
    return vdi


def _sync_status(vdi: Vdi) -> None:
    """docker inspect으로 실제 컨테이너 상태를 DB에 동기화."""
    result = _docker('inspect', '--format', '{{.State.Status}}', vdi.container_name)
    if result.returncode != 0:
        return
    actual = result.stdout.strip().upper()
    mapping = {'RUNNING': 'RUNNING', 'RESTARTING': 'RUNNING', 'EXITED': 'EXITED', 'CREATED': 'STOPPED', 'PAUSED': 'STOPPED'}
    new_status = mapping.get(actual, 'EXITED')
    if new_status != vdi.status:
        vdi.status = new_status
        vdi.updated_at = datetime.now(timezone.utc)
        db.session.commit()


def _to_dict(vdi: Vdi) -> dict:
    return {
        'vdiId':         vdi.vdi_id,
        'containerName': vdi.container_name,
        'image':         vdi.image,
        'status':        vdi.status,
        'assignedTo':    vdi.assigned_to,
        'createdAt':     vdi.created_at.isoformat(),
        'updatedAt':     vdi.updated_at.isoformat(),
    }


def _snap_to_dict(snap: VdiSnapshot) -> dict:
    return {
        'snapshotId':   snap.snapshot_id,
        'vdiId':        snap.vdi_id,
        'snapshotName': snap.snapshot_name,
        'imageTag':     snap.image_tag,
        'createdBy':    snap.created_by,
        'createdAt':    snap.created_at.isoformat(),
    }
