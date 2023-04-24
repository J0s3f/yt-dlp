# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor

from ..compat import (
    compat_b64decode,
    compat_urllib_parse_urlencode,
)
from ..utils import std_headers


class SproutVideoIE(InfoExtractor):
    _NOSCHEMA_URL = r'//videos\.sproutvideo\.com/embed/(?P<id>[a-f0-9]+)/[a-f0-9]+'
    _VALID_URL = r'https?:%s' % _NOSCHEMA_URL
    _TESTS = [{
        'url': 'https://videos.sproutvideo.com/embed/4c9dddb01910e3c9c4/0fc24387c4f24ee3',
        'md5': '1343ce1a6cb39d67889bfa07c7b02b0e',
        'info_dict': {
            'id': '4c9dddb01910e3c9c4',
            'ext': 'mp4',
            'title': 'Adrien Labaeye : Berlin, des communautés aux communs',
        }
    },
        {
            'url': 'https://videos.sproutvideo.com/embed/a79fdcb21f1be2c62e/93bf31e41e39ca27',
            'md5': 'cebae5cf558cca83271917cf4ec03f26',
            'info_dict': {
                'id': 'a79fdcb21f1be2c62e',
                'ext': 'mp4',
                'title': 'HS_01_Live Stream 2023-01-14 10:00',
            }
        }]

    @staticmethod
    def _extract_urls(webpage):
        # Fix the video URL if the iframe doesn't have a defined schema
        return [sprout.group('url') for sprout in re.finditer(
            r'<iframe[^>]+src=[\'"](?P<url>(?:https?:|)%s[^\'"]+)[\'"]' % SproutVideoIE._NOSCHEMA_URL,
            webpage)]

    def _real_extract(self, url):
        video_id = self._match_id(url)
        webpage = self._download_webpage(url, video_id, headers=std_headers)

        data = self._search_regex(r"var\s+dat\s+=\s+'([^']+)';", webpage, 'data')
        data_decoded = compat_b64decode(data).decode('utf-8')
        parsed_data = self._parse_json(data_decoded, video_id)

        # https://github.com/ytdl-org/youtube-dl/issues/16996#issuecomment-406901324
        # signature->m for manifests
        # signature->k for keys
        # signature->t for segments
        m_sign = SproutVideoIE._policy_to_qs(parsed_data, 'm')
        k_sign = SproutVideoIE._policy_to_qs(parsed_data, 'k')
        t_sign = SproutVideoIE._policy_to_qs(parsed_data, 't')

        custom_headers = {
            'Accept': '*/*',
            'Origin': 'https://videos.sproutvideo.com',
            'Referer': url
        }

        resource_url = 'https://{0}.videos.sproutvideo.com/{1}/{2}/video/index.m3u8?{3}'.format(
            parsed_data['base'], parsed_data['s3_user_hash'], parsed_data['s3_video_hash'], m_sign)

        formats = self._extract_m3u8_formats(
            resource_url, video_id, 'mp4', entry_protocol='m3u8_native', m3u8_id='hls', fatal=False,
            headers=custom_headers)

        for entry in formats:
            entry.update({
                'url': '{0}?{1}'.format(entry['url'], m_sign),
                'extra_param_to_segment_url': t_sign,
                'extra_param_to_key_url': k_sign,
                'http_headers': custom_headers
            })

        return {
            'id': video_id,
            'title': parsed_data['title'],
            'formats': formats,
        }

    @staticmethod
    def _format_qsdata(qs_data):
        parsed_dict = dict()
        for key in qs_data:
            parsed_dict[key.replace('CloudFront-', '')] = qs_data[key]
        return parsed_dict

    @staticmethod
    def _policy_to_qs(policy, key):
        sign = SproutVideoIE._format_qsdata(policy['signatures'][key])
        sign['sessionID'] = policy['sessionID']
        return compat_urllib_parse_urlencode(sign, doseq=True)