from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import Notification
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    return render(request, 'notificacoes/notification_list.html', {'notifications': notifications})

@login_required
def mark_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect('notificacoes:list')


@login_required
def mark_all_as_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "Todas as notificações foram marcadas como lidas.")
    return redirect('notificacoes:list')
