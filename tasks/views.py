from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .ai_organizer import generate_daily_plan, suggest_priority
from .forms import TaskForm
from .models import Task


def task_list(request):
    tasks = Task.objects.all()

    query = request.GET.get('q', '').strip()
    priority_filter = request.GET.get('priority', '')
    status_filter = request.GET.get('status', '')

    if query:
        tasks = tasks.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if status_filter == 'completed':
        tasks = tasks.filter(completed=True)
    elif status_filter == 'pending':
        tasks = tasks.filter(completed=False)

    context = {
        'tasks': tasks,
        'query': query,
        'priority_filter': priority_filter,
        'status_filter': status_filter,
        'total_count': Task.objects.count(),
        'pending_count': Task.objects.filter(completed=False).count(),
    }
    return render(request, 'tasks/task_list.html', context)


def task_add(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            # If the user left priority at the default and didn't touch it,
            # let the AI helper suggest one based on the title/description.
            if not request.POST.get('priority_touched'):
                task.priority = suggest_priority(task.title, task.description)
            task.save()
            messages.success(request, 'Task added.')
            return redirect('task_list')
    else:
        form = TaskForm(initial={'priority': 'medium'})
    return render(request, 'tasks/task_form.html', {'form': form, 'heading': 'Add Task'})


def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated.')
            return redirect('task_list')
    else:
        form = TaskForm(instance=task)
    return render(request, 'tasks/task_form.html', {'form': form, 'heading': 'Edit Task', 'task': task})


def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('task_list')
    return render(request, 'tasks/task_confirm_delete.html', {'task': task})


def task_toggle_complete(request, pk):
    task = get_object_or_404(Task, pk=pk)
    task.completed = not task.completed
    task.save()
    return redirect(request.META.get('HTTP_REFERER', 'task_list'))


def ai_plan(request):
    tasks = Task.objects.all()
    plan = generate_daily_plan(tasks)
    return render(request, 'tasks/ai_plan.html', {
        'plan': plan,
        'pending_tasks': tasks.filter(completed=False),
    })
