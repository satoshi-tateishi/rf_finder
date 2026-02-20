from django.http import JsonResponse

def format_channels(channels):
    if not channels: return ""
    sorted_channels = sorted(list(set(map(int, channels))))
    result = []
    i = 0
    while i < len(sorted_channels):
        start = sorted_channels[i]
        end = start
        while i + 1 < len(sorted_channels) and sorted_channels[i+1] == end + 1:
            end = sorted_channels[i+1]
            i += 1
        if end - start >= 2: result.append(f"{start}-{end}")
        else:
            for val in range(start, end + 1): result.append(str(val))
        i += 1
    return ", ".join(result)

def api_success(data=None):
    return JsonResponse({
        'status': 'success',
        'data': data
    }, json_dumps_params={'ensure_ascii': False})

def api_error(message, status=400, errors=None):
    payload = {
        'status': 'error',
        'message': message
    }
    if errors:
        payload['errors'] = errors
    return JsonResponse(payload, status=status, json_dumps_params={'ensure_ascii': False})
