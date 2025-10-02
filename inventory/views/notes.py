"""
Notes views for simple user notepad functionality.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..forms import NoteForm
from ..models import Note


@login_required
def notes_list(request):
    """List all notes for the current user."""
    notes = Note.objects.filter(user=request.user)
    return render(request, 'inventory/notes_list.html', {
        'notes': notes,
    })


@login_required
def note_create(request):
    """Create a new note."""
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.save()
            messages.success(request, 'Note created successfully.')
            return redirect('inventory:notes_list')
    else:
        form = NoteForm()

    return render(request, 'inventory/note_form.html', {
        'form': form,
        'title': 'New Note',
    })


@login_required
def note_edit(request, pk):
    """Edit an existing note."""
    note = get_object_or_404(Note, pk=pk, user=request.user)

    if request.method == 'POST':
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated successfully.')
            return redirect('inventory:notes_list')
    else:
        form = NoteForm(instance=note)

    return render(request, 'inventory/note_form.html', {
        'form': form,
        'note': note,
        'title': 'Edit Note',
    })


@login_required
def note_delete(request, pk):
    """Delete a note."""
    note = get_object_or_404(Note, pk=pk, user=request.user)

    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted successfully.')
        return redirect('inventory:notes_list')

    return render(request, 'inventory/note_confirm_delete.html', {
        'note': note,
    })
