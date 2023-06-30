import time
from decimal import Decimal

from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView, ListView
from django.db.models import Count

from .forms import CalcConfigForm, ColnectCreateForm, UserStampCreateForm
from .models import StampSample, UserStamp, Desk, DeskType


def root_view(request):
    return HttpResponseRedirect(reverse('combinations:user-stamps'))
    # if request.method == 'POST':
    #     if all(field in request.POST.keys() for field in CalcConfigForm.declared_fields):
    #         new_settings = {
    #             'stamps_count': int(request.POST['stamps_count']),
    #             'target_value': Decimal(request.POST['target_value']),
    #             'max_value': Decimal(request.POST['max_value']),
    #         }
    #
    #         request.user.calc_settings = new_settings
    #         request.user.save()
    #
    # # combs = stamp_collection.combinations()
    #
    # request.user.refresh_from_db()
    # form = CalcConfigForm(initial=request.user.calc_settings)
    #
    # context = {
    #     'form': form,
    #     # 'stamp_collection': stamp_collection,
    #     # 'combs': combs,
    # }
    # return render(request, 'combinations/index.html', context)


class StampSampleListView(ListView):
    model = StampSample
    template_name = 'combinations/stamp-sample-list.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ColnectCreateForm()
        return context


@require_http_methods(['GET', 'POST'])
def samples_create_from_colnect_view(request):
    if request.method == 'POST':
        form = ColnectCreateForm(request.POST)
        if form.is_valid():
            for url in form.cleaned_data['urls'].split('\n'):
                StampSample.objects.from_colnect(url.strip())
                time.sleep(5)

    return HttpResponseRedirect(reverse('combinations:samples'))


class StampSampleColnectView(View):
    def get(self, request, *args, **kwargs):
        view = StampSampleListView.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = samples_create_from_colnect_view
        return view(request, *args, **kwargs)


def user_stamp_view(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    if request.method == 'POST':
        form = UserStampCreateForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            for _ in range(int(data['quantity'])):
                desk = Desk.objects.get(
                    user=request.user,
                    type=DeskType.AVAILABLE,
                )
                UserStamp.objects.create(
                    sample=data['sample'],
                    comment=data['comment'],
                    user=request.user,
                    desk=desk,
                )

    form = UserStampCreateForm()

    stamps = {}
    for stamp in UserStamp.objects.filter(user=request.user):
        if stamp.sample.name not in stamps:
            stamps[stamp.sample.name] = {
                'sample': stamp.sample,
                'quantity': 0,
            }
        stamps[stamp.sample.name]['quantity'] += 1

    context = {
        'stamps': stamps,
        'form_create': form,
    }

    return render(request, 'combinations/user-stamp-list.html', context)


# class UserStampListView(ListView):
#     model = UserStamp
#     template_name = 'combinations/user-stamp-list.html'
#
#     def get_context_data(self, *, object_list=None, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['form_create'] = UserStampCreateForm()
#         return context


# class UserStampCreateView(FormView):
#     model = UserStamp
#     form_class = UserStampCreateForm
#     template_name = 'combinations/user-stamp-list.html'
#
#     def get_success_url(self):
#         return reverse('combinations:user-stamps')
#
#     def post(self, request, *args, **kwargs):
#         form = UserStampCreateForm(request.POST)
#         if form.is_valid():
#             form.cleaned_data['user'] = self.request.user
#
#         UserStamp.objects.create(**form.cleaned_data)
#         return super().post(request, *args, **kwargs)


# class UserStampView(View):
#     def get(self, request, *args, **kwargs):
#         view = UserStampListView.as_view()
#         return view(request, *args, **kwargs)
#
#     def post(self, request, *args, **kwargs):
#         view = UserStampCreateView.as_view()
#         return view(request, *args, **kwargs)


def combinations_view(request):
    if request.method == 'POST':
        if all(field in request.POST.keys() for field in CalcConfigForm.declared_fields):
            new_settings = {
                'stamps_count': int(request.POST['stamps_count']),
                'target_value': Decimal(request.POST['target_value']),
                'max_value': Decimal(request.POST['max_value']),
            }

            request.user.calc_settings = new_settings
            request.user.save()

    desk = Desk.desk_available(request.user)
    combs = desk.combinations()

    request.user.refresh_from_db()
    form = CalcConfigForm(initial=request.user.calc_settings)

    context = {
        'form': form,
        # 'stamp_collection': stamp_collection,
        'combs': combs,
    }

    return render(request, 'combinations/combinations.html', context)
