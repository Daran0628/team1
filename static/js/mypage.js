let originalMember = {}; // 🔥 취소용 원본 저장

async function loadMyPage() {
    try {
        const response = await fetch("/api/member/me", {
            headers: {
                Authorization: "Bearer " + sessionStorage.getItem("access_token")
            }
        });

        console.log("status:", response.status);

        const data = await response.json();

        const member = data.result;

        // 🔥 원본 저장 (취소용 핵심)
        originalMember = { ...member };

        console.log("accountId:", member.account_id);
        console.log("name:", member.name_ko);
        console.log("employeeNo:", member.employee_no);
        console.log("department:", member.department_name);
        console.log("email:", member.email);
        console.log("address:", member.address);
        console.log("carNum:", member.car_num);
        console.log("accountType:", member.account_type);
        console.log("workType:", member.work_type);
        console.log("lastLogin:", member.last_login);
        console.log("JS 로드됨");

        // 화면 세팅
        setField("accountId", member.account_id);
        setField("name", member.name_ko);
        setField("employeeNo", member.employee_no);
        setField("email", member.email);
        setField("address", member.address);
        setField("department", member.department_name);
        setField("carNum", member.car_num);
        setField("accountType", member.account_type);
        setField("workType", member.work_type);
        setField("lastLogin", member.last_login);

    } catch (error) {
        console.error("API 호출 실패:", error);
    }
}

function setField(id, value) {
    const textEl = document.getElementById(id + "Text");
    const inputEl = document.getElementById(id + "Input");

     // 🔥 DOM 존재 체크
    if (!textEl || !inputEl) {
        console.warn(`setField 실패: ${id} DOM 없음`);
        return;
    }

     // 🔥 null/undefined 방어
    const safeValue = (value === null || value === undefined) ? "" : value;

    textEl.textContent = safeValue;
    inputEl.value = safeValue;
}

function getField(id) {
    const inputEl = document.getElementById(id + "Input");

     if (!inputEl) {
        console.warn(`getField 실패: ${id} DOM 없음`);
        return "";
    }

    return inputEl.value ?? "";
}

loadMyPage();


// =========================
// 버튼
// =========================

const btnEdit = document.getElementById("btnEdit");
const btnSave = document.getElementById("btnSave");
const btnCancel = document.getElementById("btnCancel");


// =========================
// 수정 모드
// =========================
btnEdit.onclick = () => {

    document.querySelectorAll("span").forEach(e => {
        e.style.display = "none";
    });

    document.querySelectorAll(".edit-field").forEach(e => {
        e.style.display = "block";
    });

    btnEdit.style.display = "none";
    btnSave.style.display = "inline-block";
    btnCancel.style.display = "inline-block";
};


// =========================
// 취소 (원복)
// =========================
btnCancel.onclick = () => {

    setField("email", originalMember.email);
    setField("address", originalMember.address);
    setField("carNum", originalMember.car_num);
    setField("workType", originalMember.work_type);


    document.querySelectorAll("span").forEach(e => {
        e.style.display = "inline";
    });

    document.querySelectorAll(".edit-field").forEach(e => {
        e.style.display = "none";
    });

    btnEdit.style.display = "inline-block";
    btnSave.style.display = "none";
    btnCancel.style.display = "none";

    console.log("수정 취소 → 원복 완료");
};


// =========================
// 저장 (PUT API)
// =========================
btnSave.onclick = async () => {

    const updatedData = {
        email: getField("email"),
        address: getField("address"),
        car_num: getField("carNum"),
        department_name: getField("department"),
        work_type: getField("workType")
    };

    try {
        const response = await fetch("/api/member/me", {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                Authorization: "Bearer " + sessionStorage.getItem("access_token")
            },
            body: JSON.stringify(updatedData)
        });

        const result = await response.json();
        console.log("저장 완료:", result);

        // 🔥 1. 다시 조회해서 최신 데이터 반영
        await loadMyPage();

        // 🔥 2. 무조건 조회모드로 전환
        exitEditMode();

    } catch (error) {
        console.error("저장 실패:", error);
    }
};

function exitEditMode() {

    // span 보이기
    document.querySelectorAll("span").forEach(e => {
        e.style.display = "inline";
    });

    // input 숨기기
    document.querySelectorAll(".edit-field").forEach(e => {
        e.style.display = "none";
    });

    // 버튼 상태 복구
    btnEdit.style.display = "inline-block";
    btnSave.style.display = "none";
    btnCancel.style.display = "none";

    console.log("조회 모드로 전환 완료");
}