from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def index(request):
    """Это главная страница соцсети."""
    post_list = Post.objects.select_related("group", "author")
    paginator = Paginator(post_list, settings.COUNT_POST_IN_LIST)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
    }
    return render(request, "posts/index.html", context)


def group_posts(request, slug):
    """Это страница с постами, отфильтрованными по группам."""
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related("group")
    paginator = Paginator(post_list, settings.COUNT_POST_IN_LIST)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "group": group,
    }
    return render(request, "posts/group_list.html", context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    paginator = Paginator(post_list, settings.COUNT_POST_IN_LIST)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    following = True
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            author_id=author.id,
            user_id=request.user.id).exists()
    context = {
        "page_obj": page_obj,
        "author": author,
        "following": following,
    }
    return render(request, "posts/profile.html", context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    comments = post.comments.all()
    context = {
        "post": post,
        "form": form,
        "comments": comments,
    }
    return render(request, "posts/post_detail.html", context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        author = request.user
        post.author_id = author.id
        post.save()
        return redirect("posts:profile", username=author.username)
    return render(request, "posts/create_post.html", {"form": form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect(post)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect(post)
    is_edit = True
    context = {
        "form": form,
        "post_id": post_id,
        "is_edit": is_edit,
    }
    return render(request, "posts/create_post.html", context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect(post)


@login_required
def follow_index(request):
    subscriber = get_object_or_404(User, username=request.user)
    authors = subscriber.follower.all().values_list('author')
    post_list = Post.objects.filter(author_id__in=authors)
    paginator = Paginator(post_list, settings.COUNT_POST_IN_LIST)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
    }
    return render(request, "posts/follow.html", context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user.id == author.id:
        return redirect("posts:profile", username)
    Follow.objects.get_or_create(user=request.user, author=author)
    return redirect("posts:follow_index")


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user.id == author.id:
        return redirect("posts:profile", username)
    Follow.objects.filter(user=request.user, author=author.id).delete()
    return redirect("posts:follow_index")
