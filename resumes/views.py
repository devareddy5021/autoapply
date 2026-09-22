from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Resume
from .forms import ResumeUploadForm

@login_required
def resume_list_view(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()
            messages.success(request, f"Resume '{resume.name}' uploaded and processed successfully!")
            return redirect('resumes:list')
        else:
            messages.error(request, "Error uploading resume. Please check the file.")
    else:
        form = ResumeUploadForm()

    user_resumes = Resume.objects.filter(user=request.user)
    return render(request, 'resumes/resume_list.html', {
        'resumes': user_resumes,
        'form': form,
    })


@login_required
def resume_detail_view(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    return render(request, 'resumes/resume_detail.html', {
        'resume': resume,
    })


@login_required
def set_default_resume_view(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    resume.is_default = True
    resume.save()
    messages.success(request, f"'{resume.name}' is now set as your default resume.")
    return redirect('resumes:list')


@login_required
def delete_resume_view(request, pk):
    resume = get_object_or_404(Resume, pk=pk, user=request.user)
    name = resume.name
    resume.file.delete(save=False)
    resume.delete()
    messages.info(request, f"Resume '{name}' was deleted.")
    return redirect('resumes:list')
