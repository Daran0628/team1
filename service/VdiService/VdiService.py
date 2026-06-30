import subprocess
from datetime import datetime, timezone

from extensions import db
from domain.model.Vdi import Vdi, VdiSnapshot
from core.response.ErrorStatus import ErrorStatus


class VdiException(Exception):
    def __init__(self, error_status: ErrorStatus, detail: str = ""):
        self.error_status = error_status
        self.detail = detail


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

    result = _docker('run', '-d', '--name', container_name, image)
    if result.returncode != 0:
        raise VdiException(ErrorStatus.VDI_CREATE_FAILED, result.stderr.strip())

    vdi = Vdi(container_name=container_name, image=image, status='RUNNING', assigned_to=member_id)
    db.session.add(vdi)
    db.session.commit()
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
    _get_or_404(vdi_id)
    snaps = VdiSnapshot.query.filter_by(vdi_id=vdi_id).order_by(VdiSnapshot.created_at.desc()).all()
    return [_snap_to_dict(s) for s in snaps]


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
    mapping = {'RUNNING': 'RUNNING', 'EXITED': 'EXITED', 'CREATED': 'STOPPED', 'PAUSED': 'STOPPED'}
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
