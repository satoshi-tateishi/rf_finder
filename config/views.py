from django.http import HttpResponse


def healthcheck(_request):
    """コンテナ内のWebアプリケーションが応答可能なら204を返す。"""
    return HttpResponse(status=204)
