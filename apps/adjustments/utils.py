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
