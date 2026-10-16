from __future__ import annotations

from typing import Sequence

from services.livestream.composer import StreamSegment


def build_playlist(
    matches: Sequence[StreamSegment] = (),
    highlights: Sequence[StreamSegment] = (),
    debates: Sequence[StreamSegment] = (),
    ads: Sequence[StreamSegment] = (),
    *,
    sponsor_interval: int = 2,
) -> list[StreamSegment]:
    playlist: list[StreamSegment] = []
    match_list = list(matches)
    highlight_list = list(highlights)
    debate_list = list(debates)
    ad_list = list(ads)
    if not any((match_list, highlight_list, debate_list, ad_list)):
        return []
    longest = max(len(match_list), len(highlight_list), len(debate_list), 1)
    non_ad_count = 0
    for index in range(longest):
        for bucket in (match_list, highlight_list, debate_list):
            if index >= len(bucket):
                continue
            playlist.append(bucket[index])
            non_ad_count += 1
            if ad_list and sponsor_interval > 0 and non_ad_count % sponsor_interval == 0:
                playlist.append(ad_list[(non_ad_count // sponsor_interval - 1) % len(ad_list)])
    if not playlist and ad_list:
        playlist.extend(ad_list)
    return playlist
