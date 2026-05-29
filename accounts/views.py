from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# View Đăng nhập
def login_view(request):
    if request.user.is_authenticated:
        return redirect('summary_reconciliation_view')  # Nếu đã đăng nhập, chuyển về trang chính
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Đăng nhập thành công!')
            return redirect('summary_reconciliation_view')  # Chuyển hướng sau khi đăng nhập thành công
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')
    return render(request, 'login.html')

# View Đăng xuất
def logout_view(request):
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công.')
    return redirect('login')

