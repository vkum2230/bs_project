#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
骑行记录持久化仓库 (RideRepository)

职责：
- 保存单次骑行为 FIT + GPX 文件
- 列出历史骑行记录
- 读取 GPX 轨迹用于地图回放
- 删除骑行记录

依赖安装（树莓派）：
    pip3 install --break-system-packages garmin-fit-sdk gpxpy
"""

import os
import json
import glob
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from core.protocol import RideSummary, TrackPoint, GPSPoint

# ------------------------------------------------------------------------------
# 可选依赖：FIT 写入
# ------------------------------------------------------------------------------
try:
    from garmin_fit_sdk import Stream, Profile
    from garmin_fit_sdk.encoder import Encoder
    _FIT_AVAILABLE = True
except Exception as _e:
    print(f"[RideRepository] FIT SDK 未安装，将只生成 GPX: {_e}")
    _FIT_AVAILABLE = False

# ------------------------------------------------------------------------------
# 可选依赖：GPX 读写
# ------------------------------------------------------------------------------
try:
    import gpxpy
    import gpxpy.gpx
    _GPX_AVAILABLE = True
except Exception as _e:
    print(f"[RideRepository] gpxpy 未安装，无法生成 GPX: {_e}")
    _GPX_AVAILABLE = False

# FIT epoch 偏移（1990-01-01 到 1970-01-01 的秒数）
_FIT_EPOCH_OFFSET = 631065600


def _to_fit_timestamp(ts: float) -> int:
    return int(ts) - _FIT_EPOCH_OFFSET


def _to_semicircles(deg: float) -> int:
    return int(deg * (2 ** 31 / 180.0))


def _enum_val(type_name: str, value_name: str) -> int:
    """从 Profile 类型定义中查找枚举值"""
    if not _FIT_AVAILABLE:
        return 0
    try:
        from garmin_fit_sdk import Profile
        enum_dict = Profile["types"][type_name]
        for k, v in enum_dict.items():
            if v == value_name:
                # 键可能是十六进制字符串如 '0xF7'
                return int(k, 0)
    except Exception:
        pass
    return 0


class RideRepository:
    """骑行记录持久化管理器"""

    def __init__(self, base_dir: str = "~/smartride/rides"):
        self.base_dir = os.path.expanduser(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    # --------------------------------------------------------------------------
    # 公开 API
    # --------------------------------------------------------------------------

    def save_ride(self, summary: RideSummary, track_points: List[TrackPoint]) -> str:
        """
        保存骑行记录
        返回 ride_id (如 ride_20260414_143052)
        """
        ride_id = self._generate_ride_id(summary.start_time)
        date_dir = self._get_date_dir(summary.start_time)
        gpx_path = os.path.join(date_dir, f"{ride_id}.gpx")
        fit_path = os.path.join(date_dir, f"{ride_id}.fit")
        meta_path = os.path.join(date_dir, f"{ride_id}.json")

        written_gpx = False
        written_fit = False

        if _GPX_AVAILABLE:
            try:
                self._write_gpx(gpx_path, summary, track_points)
                written_gpx = True
            except Exception as e:
                print(f"[RideRepository] GPX 写入失败: {e}")
                gpx_path = ""
        else:
            gpx_path = ""

        if _FIT_AVAILABLE and track_points:
            try:
                self._write_fit(fit_path, summary, track_points)
                written_fit = True
            except Exception as e:
                print(f"[RideRepository] FIT 写入失败: {e}")
                fit_path = ""
        else:
            fit_path = ""

        # 元数据 JSON（方便 HistoryPage 快速读取）
        self._write_meta(meta_path, summary, ride_id, gpx_path if written_gpx else "", fit_path if written_fit else "")

        summary.file_path = (gpx_path if written_gpx else "") or (fit_path if written_fit else "")
        print(f"[RideRepository] 骑行记录已保存: {ride_id} "
              f"(GPX={'✓' if written_gpx else '✗'}, FIT={'✓' if written_fit else '✗'})")
        return ride_id

    def list_rides(self, limit: int = 50) -> List[Dict[str, Any]]:
        """返回历史骑行列表（按时间倒序），用于 HistoryPage"""
        rides = []
        pattern = os.path.join(self.base_dir, "**", "*.json")
        meta_files = glob.glob(pattern, recursive=True)
        for mf in sorted(meta_files, reverse=True):
            try:
                with open(mf, "r", encoding="utf-8") as f:
                    rides.append(json.load(f))
            except Exception:
                continue
        return rides[:limit]

    def get_ride(self, ride_id: str) -> Optional[Dict[str, Any]]:
        """读取单次骑行元数据 + GPX 轨迹点（用于地图回放）"""
        for root, _, files in os.walk(self.base_dir):
            if f"{ride_id}.json" in files:
                meta_path = os.path.join(root, f"{ride_id}.json")
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    gpx_path = meta.get("gpx_path", "")
                    if gpx_path and os.path.exists(gpx_path):
                        meta["track_points"] = self._read_gpx(gpx_path)
                    else:
                        meta["track_points"] = []
                    return meta
                except Exception as e:
                    print(f"[RideRepository] 读取骑行记录失败: {e}")
                    return None
        return None

    def delete_ride(self, ride_id: str) -> bool:
        """删除某次骑行的所有文件（json + gpx + fit）"""
        for root, _, files in os.walk(self.base_dir):
            if f"{ride_id}.json" in files:
                try:
                    for ext in [".json", ".gpx", ".fit"]:
                        fp = os.path.join(root, f"{ride_id}{ext}")
                        if os.path.exists(fp):
                            os.remove(fp)
                    return True
                except Exception as e:
                    print(f"[RideRepository] 删除失败: {e}")
                    return False
        return False

    # --------------------------------------------------------------------------
    # 内部工具
    # --------------------------------------------------------------------------

    @staticmethod
    def _generate_ride_id(start_time: float) -> str:
        dt = datetime.fromtimestamp(start_time)
        return dt.strftime("ride_%Y%m%d_%H%M%S")

    def _get_date_dir(self, start_time: float) -> str:
        dt = datetime.fromtimestamp(start_time)
        date_dir = os.path.join(self.base_dir, dt.strftime("%Y-%m-%d"))
        os.makedirs(date_dir, exist_ok=True)
        return date_dir

    def _write_meta(self, path: str, summary: RideSummary, ride_id: str, gpx_path: str, fit_path: str):
        meta = {
            "id": ride_id,
            "start_time": summary.start_time,
            "end_time": summary.end_time,
            "total_distance": round(summary.total_distance, 2),
            "total_time": summary.total_time,
            "moving_time": summary.moving_time,
            "avg_speed": summary.avg_speed,
            "max_speed": summary.max_speed,
            "avg_power": summary.avg_power,
            "max_power": summary.max_power,
            "avg_hr": summary.avg_hr,
            "max_hr": summary.max_hr,
            "total_elevation_gain": round(summary.total_elevation_gain, 1),
            "max_elevation_gain": round(summary.max_elevation_gain, 1),
            "calories": summary.calories,
            "gpx_path": gpx_path,
            "fit_path": fit_path,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    # --------------------------------------------------------------------------
    # GPX
    # --------------------------------------------------------------------------

    def _write_gpx(self, path: str, summary: RideSummary, points: List[TrackPoint]):
        gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for p in points:
            pt = gpxpy.gpx.GPXTrackPoint(
                latitude=p.gps.lat,
                longitude=p.gps.lon,
                elevation=p.altitude if p.altitude else None,
                time=datetime.fromtimestamp(p.gps.timestamp, tz=timezone.utc),
            )
            if p.power and p.power > 0:
                pt.power = int(p.power)
            segment.points.append(pt)

        xml_str = gpx.to_xml()
        with open(path, "w", encoding="utf-8") as f:
            f.write(xml_str)

    def _read_gpx(self, path: str) -> List[Dict[str, Any]]:
        points = []
        with open(path, "r", encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    points.append({
                        "lat": pt.latitude,
                        "lon": pt.longitude,
                        "altitude": pt.elevation,
                        "time": pt.time.timestamp() if pt.time else 0,
                    })
        return points

    # --------------------------------------------------------------------------
    # FIT
    # --------------------------------------------------------------------------

    def _write_fit(self, path: str, summary: RideSummary, points: List[TrackPoint]):
        if not _FIT_AVAILABLE:
            return

        from garmin_fit_sdk import Encoder

        encoder = Encoder()

        fit_start = _to_fit_timestamp(summary.start_time)
        fit_end = _to_fit_timestamp(summary.end_time) if summary.end_time else fit_start
        total_time_ms = int(summary.total_time * 1000)
        moving_time_ms = int(summary.moving_time * 1000)
        total_distance_cm = int(summary.total_distance * 100000)

        # ---- FileId ----
        encoder.write_mesg({
            "mesg_num": 0,
            "type": _enum_val("file", "activity"),
            "manufacturer": _enum_val("manufacturer", "development"),
            "product": 0,
            "time_created": fit_start,
        })

        # ---- Event: start ----
        encoder.write_mesg({
            "mesg_num": 21,
            "timestamp": fit_start,
            "event": _enum_val("event", "timer"),
            "event_type": _enum_val("event_type", "start"),
        })

        # ---- Records ----
        cumulative_distance = 0.0
        last_ts = fit_start

        for i, p in enumerate(points):
            ts = _to_fit_timestamp(p.gps.timestamp)
            if ts < fit_start:
                ts = fit_start
            if ts <= last_ts and i > 0:
                ts = last_ts + 1
            last_ts = ts

            # 简单累计距离（cm）
            if i > 0:
                dt = max(1, ts - _to_fit_timestamp(points[i - 1].gps.timestamp))
                cumulative_distance += p.speed * dt / 3600.0 * 100000.0

            rec = {
                "mesg_num": 20,
                "timestamp": ts,
                "distance": int(cumulative_distance),
            }
            if p.gps.lat:
                rec["position_lat"] = _to_semicircles(p.gps.lat)
            if p.gps.lon:
                rec["position_long"] = _to_semicircles(p.gps.lon)
            if p.altitude:
                rec["altitude"] = int(p.altitude * 5 + 5000)
            if p.speed >= 0:
                rec["speed"] = int(p.speed * 1000)  # mm/s
            if p.power > 0:
                rec["power"] = int(p.power)
            if p.cadence > 0:
                rec["cadence"] = int(p.cadence)
            if p.heart_rate > 0:
                rec["heart_rate"] = int(p.heart_rate)
            encoder.write_mesg(rec)

        # ---- Event: stop ----
        encoder.write_mesg({
            "mesg_num": 21,
            "timestamp": fit_end,
            "event": _enum_val("event", "timer"),
            "event_type": _enum_val("event_type", "stop_all"),
        })

        # ---- Lap ----
        lap = {
            "mesg_num": 19,
            "timestamp": fit_end,
            "start_time": fit_start,
            "total_elapsed_time": total_time_ms,
            "total_timer_time": moving_time_ms,
            "total_distance": total_distance_cm,
        }
        if summary.avg_speed >= 0:
            lap["avg_speed"] = int(summary.avg_speed * 1000)
        if summary.max_speed >= 0:
            lap["max_speed"] = int(summary.max_speed * 1000)
        if summary.avg_power > 0:
            lap["avg_power"] = int(summary.avg_power)
        if summary.max_power > 0:
            lap["max_power"] = int(summary.max_power)
        if summary.avg_hr > 0:
            lap["avg_heart_rate"] = int(summary.avg_hr)
        if summary.max_hr > 0:
            lap["max_heart_rate"] = int(summary.max_hr)
        if summary.total_elevation_gain > 0:
            lap["total_ascent"] = int(summary.total_elevation_gain * 10)
        encoder.write_mesg(lap)

        # ---- Session ----
        session = {
            "mesg_num": 18,
            "timestamp": fit_end,
            "start_time": fit_start,
            "sport": _enum_val("sport", "cycling"),
            "sub_sport": _enum_val("sub_sport", "generic"),
            "total_elapsed_time": total_time_ms,
            "total_timer_time": moving_time_ms,
            "total_distance": total_distance_cm,
            "num_laps": 1,
        }
        if summary.avg_speed >= 0:
            session["avg_speed"] = int(summary.avg_speed * 1000)
        if summary.max_speed >= 0:
            session["max_speed"] = int(summary.max_speed * 1000)
        if summary.avg_power > 0:
            session["avg_power"] = int(summary.avg_power)
        if summary.max_power > 0:
            session["max_power"] = int(summary.max_power)
        if summary.avg_hr > 0:
            session["avg_heart_rate"] = int(summary.avg_hr)
        if summary.max_hr > 0:
            session["max_heart_rate"] = int(summary.max_hr)
        if summary.total_elevation_gain > 0:
            session["total_ascent"] = int(summary.total_elevation_gain * 10)
        if summary.calories > 0:
            session["total_calories"] = int(summary.calories)
        encoder.write_mesg(session)

        # ---- Activity ----
        encoder.write_mesg({
            "mesg_num": 34,
            "timestamp": fit_end,
            "num_sessions": 1,
            "type": _enum_val("activity", "manual"),
        })

        data = encoder.close()
        with open(path, "wb") as f:
            f.write(data)
