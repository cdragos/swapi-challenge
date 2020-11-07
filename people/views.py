from typing import List
from uuid import uuid4

from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from petl.io.csv_py3 import CSVView
from petl.transform.basics import CutOutView
from petl.util.base import DataView
import petl as etl

from people.models import CollectionModel
from people.services import fetch_data


DEFAULT_LIMIT = 10


def dashboard(request: HttpRequest) -> HttpResponse:
    collections: QuerySet = CollectionModel.objects.all()
    return render(request, 'dashboard.html', {
        'collections': collections,
    })


def collection(request: HttpRequest, pk: int) -> HttpResponse:
    limit = int(request.GET.get('limit', DEFAULT_LIMIT))
    columns: List[str] = request.GET.getlist('columns')

    collection: CollectionModel = get_object_or_404(CollectionModel, pk=pk)
    table: CSVView = etl.fromcsv(f'{settings.DATA_PATH}/{collection.filename}')

    if columns:
        table: CutOutView = table.valuecounts(*columns).cutout('frequency')
        headers: tuple = etl.header(table)
        rows: DataView = table.data()
        limit = None
    else:
        rows: DataView = table.data(0, limit)
        headers: tuple = etl.header(table)
        limit = limit + DEFAULT_LIMIT

    return render(request, 'collection.html', {
        'collection': collection,
        'headers': headers,
        'rows': rows,
        'limit': limit,
    })


def fetch(request: HttpRequest) -> HttpResponseRedirect:
    filename: str = f'{uuid4().hex}.csv'
    fetch_data(filename)
    CollectionModel.objects.create(filename=filename)
    return redirect('dashboard')
