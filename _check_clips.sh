#!/bin/bash
# Сколько записей «Аниме-сонглесса» уже полноценные (20,5 с, не петля).
# Запуск: bash /opt/greenhouse/check_clips.sh
set -e

q() { sudo -u postgres psql -d greenhouse -Atc "$1"; }

total=$(q "SELECT count(*) FROM songless_tracks")
real=$(q "SELECT count(*) FROM audio_clips WHERE game='songless' AND source <> 'loop'")
loops=$(q "SELECT count(*) FROM audio_clips WHERE game='songless' AND source = 'loop'")
short=$(q "SELECT count(*) FROM songless_tracks WHERE clip_length < 20")
size=$(q "SELECT pg_size_pretty(sum(octet_length(data))::bigint) FROM audio_clips WHERE game='songless'")

echo "Треков всего:              $total"
echo "Полноценных записей:       $real"
echo "Ещё петли (8 с × 2,5):     $loops"
echo "Коротких (8 с):            $short"
echo "Звук в базе:               $size"
echo
echo "Служба догрузки:           $(systemctl is-active clipfill.service)"
echo "Перезапусков службы:       $(systemctl show -p NRestarts --value clipfill.service)"
echo "Последние строки лога:"
tail -4 /var/log/clipfill.log 2>/dev/null | sed 's/^/  /' || echo "  (лог пуст)"