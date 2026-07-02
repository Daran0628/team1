const _role = sessionStorage.getItem('role');
if (_role === 'ADMIN' || _role === 'SUPERADMIN') {
    const _adminMenu = document.getElementById('admin-menu');
    const _iamMenu    = document.getElementById('iam-menu');
    if (_adminMenu) _adminMenu.style.display = 'flex';
    if (_iamMenu)   _iamMenu.style.display = 'flex';
}
function logout() {
    sessionStorage.clear();
    location.replace('/login');
}
document.getElementById('logout-link')?.addEventListener('click', logout);