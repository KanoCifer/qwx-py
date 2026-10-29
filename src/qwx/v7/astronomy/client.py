"""旧一代天文数据接口（/v7/astronomy/*）的调用入口。

日出日落、月升月落与太阳高度角至今只有 v7 版本。

这一代的位置是查询参数 `location=经度,纬度`（经度在前），不认地名；
太阳高度角端点只认坐标，LocationID 会被上游拒绝。

同步与异步共用同一套端点方法体，只是发送层一个同步一个协程。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from qwx._cachekey import Family, Key, Params
from qwx._service import Service
from qwx.errors import InvalidLocationError, InvalidParameterError
from qwx.location import Location
from qwx.request import Request

from .types import (
    AngleResult,
    EndpointAngle,
    EndpointMoon,
    EndpointSun,
    MoonResult,
    Options,
    SunResult,
)

__all__ = ["AstronomyService", "AsyncAstronomyService"]

CACHE_TTL = timedelta(seconds=86400)
"""天文接口的默认缓存时长：这些数据按日期固定，一天之内不变。"""


def _require_id_or_coord(loc: Location) -> None:
    """要求位置是坐标对或 LocationID。

    上游的 locationIdCoordQuery 只认这两种形态，地名会被拒绝。
    """
    if not loc.has_coordinates() and not loc.id:
        raise InvalidLocationError("qwx: astronomy requires coordinates or a LocationID")


def _require_coord(loc: Location) -> None:
    """要求位置是坐标对。

    上游的 lonlatQuery 只认坐标对，LocationID 会被拒绝。
    """
    if not loc.has_coordinates():
        raise InvalidLocationError("qwx: solar elevation angle requires coordinates")


def _validate_date(date: str) -> None:
    """校验日期格式为 yyyyMMdd 且是真实日期。

    日期范围（上游最多接受未来 60 天，含今天）不在这里判断 —— 那要拿
    「今天」比，上游自己会回 400。
    """
    if len(date) != 8 or not date.isdigit():
        raise InvalidParameterError(f"qwx: date {date!r} must be in yyyyMMdd format")
    try:
        datetime.strptime(date, "%Y%m%d")
    except ValueError:
        raise InvalidParameterError(f"qwx: date {date!r} is not a valid calendar date") from None


def _validate_time(time_str: str) -> None:
    """校验时间格式为 HHmm，取值 0000~2359。"""
    if len(time_str) != 4 or not time_str.isdigit():
        raise InvalidParameterError(f"qwx: time {time_str!r} must be in HHmm format")
    hours = int(time_str[:2])
    minutes = int(time_str[2:])
    if hours > 23 or minutes > 59:
        raise InvalidParameterError(f"qwx: time {time_str!r} is not a valid 24-hour time")


def _validate_timezone(tz: str) -> None:
    """校验时区偏移格式为 HHmm，正负号可省。

    取值范围 [-12:00,+14:00] —— 真实存在的时区偏移都在这个区间内。
    """
    negative = False
    digits = tz
    if len(tz) == 5 and tz[0] in "+-":
        negative = tz[0] == "-"
        digits = tz[1:]
    elif len(tz) != 4:
        raise InvalidParameterError(f"qwx: tz {tz!r} must be in HHmm format, like 0800 or -0530")
    if not digits.isdigit():
        raise InvalidParameterError(f"qwx: tz {tz!r} must be in HHmm format, like 0800 or -0530")
    hours = int(digits[:2])
    minutes = int(digits[2:])
    max_hours = 12 if negative else 14
    if hours > max_hours or minutes > 59:
        raise InvalidParameterError(
            f"qwx: tz {tz!r} is out of the UTC offset range [-12:00,+14:00]"
        )


class _AstronomyCalls(Service):
    """天文端点族的方法体。同步与异步共用。"""

    def _sun_call(self, loc: Location, date: str) -> Any:
        """日出日落的请求参数与发送。"""
        _require_id_or_coord(loc)
        _validate_date(date)
        return self._call(
            Request(
                method="GET",
                path="/v7/astronomy/sun",
                query={"location": loc.query(), "date": date},
                endpoint=EndpointSun,
                cache_key=str(Key(Family.ASTRONOMY).path("sun", loc.query(), date)),
                ttl=CACHE_TTL,
                out=SunResult,
            )
        )

    def _moon_call(self, loc: Location, date: str, opts: Options | None = None) -> Any:
        """月升月落与月相的请求参数与发送。"""
        _require_id_or_coord(loc)
        _validate_date(date)
        options = opts if opts is not None else Options()
        options.lang.validate()
        params = Params(lang=options.lang.api)
        query = params.query()
        query["location"] = loc.query()
        query["date"] = date
        return self._call(
            Request(
                method="GET",
                path="/v7/astronomy/moon",
                query=query,
                endpoint=EndpointMoon,
                cache_key=str(Key(Family.ASTRONOMY).path("moon", loc.query(), date).params(params)),
                ttl=CACHE_TTL,
                out=MoonResult,
            )
        )

    def _solar_elevation_angle_call(
        self,
        loc: Location,
        date: str,
        time_str: str,
        tz: str,
        alt: int,
    ) -> Any:
        """太阳高度角的请求参数与发送。"""
        _require_coord(loc)
        _validate_date(date)
        _validate_time(time_str)
        _validate_timezone(tz)
        if alt < 0:
            raise InvalidParameterError(f"qwx: altitude {alt} must not be negative")
        return self._call(
            Request(
                method="GET",
                path="/v7/astronomy/solar-elevation-angle",
                query={
                    "location": loc.query(),
                    "date": date,
                    "time": time_str,
                    "tz": tz,
                    "alt": str(alt),
                },
                endpoint=EndpointAngle,
                cache_key=str(
                    Key(Family.ASTRONOMY).path("angle", loc.query(), date, time_str, tz, str(alt))
                ),
                ttl=CACHE_TTL,
                out=AngleResult,
            )
        )


class AstronomyService(_AstronomyCalls):
    """同步天文服务客户端。

    用基础客户端构造，无状态，可并发共享：

        service = AstronomyService(client)
        sun = service.sun(Location(lat=39.92, lon=116.41), "20260531")
    """

    def sun(self, loc: Location, date: str) -> SunResult:
        """查询日出日落。

        调 GET /v7/astronomy/sun?location=...&date=yyyyMMdd。

        loc 是坐标对或 LocationID —— 上游这个参数是 locationIdCoordQuery，
        认 "经度,纬度" 与 LocationID，**不认地名**。只有地名的位置先用
        geo 包换成坐标或 LocationID。

        date 必填，格式 "yyyyMMdd"。客户端只校验格式（8 位数字且是真实
        日期），日期范围交给上游判断：**上游最多接受未来 60 天（含今天）**，
        超范围回 400。

        缓存键：`qwx:astronomy:sun:<location>:<date>`。

        默认 TTL 24 小时 —— 数据按日期固定，一天之内不变。可用 TTLPolicy
        按 `EndpointSun` 覆盖。

        日出日落可能为空：高纬度与极昼极夜地区上游给 null，
        `SunResult.sunrise` 与 `SunResult.sunset` 此时是 None。
        """
        return cast(SunResult, self._sun_call(loc, date))

    def moon(self, loc: Location, date: str, opts: Options | None = None) -> MoonResult:
        """查询月升月落与月相。

        调 GET /v7/astronomy/moon?location=...&date=yyyyMMdd&lang=...。

        loc 是坐标对或 LocationID —— 同 [AstronomyService.sun]，上游不认
        地名。

        date 必填，格式 "yyyyMMdd"。客户端只校验格式，日期范围交给上游
        判断：**上游最多接受未来 60 天（含今天）**。

        opts.lang 是语言，如 `Lang.ZH`。留空用上游默认。月相名称与图标随
        语言变，所以语言进缓存键。

        缓存键：`qwx:astronomy:moon:<location>:<date>` 加语言后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 `EndpointMoon` 覆盖。

        月升月落可能为空（`MoonResult.moonrise` / `MoonResult.moonset` 为
        None）；月相列表长度不固定，不要假设。
        """
        return cast(MoonResult, self._moon_call(loc, date, opts))

    def solar_elevation_angle(
        self,
        loc: Location,
        date: str,
        time_str: str,
        tz: str,
        alt: int,
    ) -> AngleResult:
        """查询指定时刻的太阳高度角与方位角。

        调 GET /v7/astronomy/solar-elevation-angle?location=...&date=...&time=...&tz=...&alt=...。

        loc **只认坐标对** —— 上游这个端点用 lonlatQuery，LocationID 会被
        拒绝。

        date 必填，格式 "yyyyMMdd"，客户端只校验格式（日期范围交给上游）。

        time_str 必填，格式 "HHmm" 24 时制，取值 0000~2359。

        tz 必填，查询地区所在时区的 UTC 偏移，形如 "0800"、"-0530"（正负号
        可省），取值范围 [-12:00,+14:00]。

        alt 必填，海拔高度（米），负数非法 —— 海拔不会是负的。

        参数越界抛 [qwx.errors.InvalidParameterError]，位置形态不对抛
        [qwx.errors.InvalidLocationError]，两种都在打上游之前返回。

        缓存键：`qwx:astronomy:angle:<location>:<date>:<time>:<tz>:<alt>`。
        date、time、tz、alt 都影响结果，都要进键。

        默认 TTL 24 小时，可用 TTLPolicy 按 `EndpointAngle` 覆盖。

        上游这个端点的响应里没有 updateTime 与 fxLink。
        """
        return cast(AngleResult, self._solar_elevation_angle_call(loc, date, time_str, tz, alt))


class AsyncAstronomyService(_AstronomyCalls):
    """异步天文服务客户端。

    用异步基础客户端构造，无状态，可并发共享：

        service = AsyncAstronomyService(async_client)
        sun = await service.sun(Location(lat=39.92, lon=116.41), "20260531")
    """

    async def sun(self, loc: Location, date: str) -> SunResult:
        """查询日出日落。

        调 GET /v7/astronomy/sun?location=...&date=yyyyMMdd。

        loc 是坐标对或 LocationID，不认地名。

        date 必填，格式 "yyyyMMdd"；日期范围交给上游（最多未来 60 天）。

        缓存键：`qwx:astronomy:sun:<location>:<date>`。

        默认 TTL 24 小时，可用 TTLPolicy 按 `EndpointSun` 覆盖。
        """
        return cast(SunResult, await self._sun_call(loc, date))

    async def moon(self, loc: Location, date: str, opts: Options | None = None) -> MoonResult:
        """查询月升月落与月相。

        调 GET /v7/astronomy/moon?location=...&date=yyyyMMdd&lang=...。

        loc 是坐标对或 LocationID，不认地名。

        date 必填，格式 "yyyyMMdd"；日期范围交给上游（最多未来 60 天）。

        缓存键：`qwx:astronomy:moon:<location>:<date>` 加语言后缀。

        默认 TTL 24 小时，可用 TTLPolicy 按 `EndpointMoon` 覆盖。
        """
        return cast(MoonResult, await self._moon_call(loc, date, opts))

    async def solar_elevation_angle(
        self,
        loc: Location,
        date: str,
        time_str: str,
        tz: str,
        alt: int,
    ) -> AngleResult:
        """查询指定时刻的太阳高度角与方位角。

        调 GET /v7/astronomy/solar-elevation-angle?location=...&date=...&time=...&tz=...&alt=...。

        loc 只认坐标对。

        date 必填，格式 "yyyyMMdd"；time_str 必填，格式 "HHmm"；tz 必填，
        范围 [-12:00,+14:00]；alt 必填，不能为负。越界在打上游之前抛
        [qwx.errors.InvalidParameterError]。

        缓存键：`qwx:astronomy:angle:<location>:<date>:<time>:<tz>:<alt>`。

        默认 TTL 24 小时，可用 TTLPolicy 按 `EndpointAngle` 覆盖。
        """
        return cast(
            AngleResult,
            await self._solar_elevation_angle_call(loc, date, time_str, tz, alt),
        )
