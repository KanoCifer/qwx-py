"""预警接口的结果类型。"""

from __future__ import annotations

from qwx.v1.alert.types import Alert, Color, Endpoint, EventType, MessageType, Result

PAYLOAD = {
    "metadata": {"tag": "t", "zeroResult": False},
    "alerts": [
        {
            "id": "202510241119105837988676",
            "senderName": "临桂区气象台",
            "issuedTime": "2025-10-24T11:19+08:00",
            "messageType": {"code": "update", "supersedes": ["202510181140100706230391"]},
            "eventType": {"name": "大风", "code": "1006"},
            "severity": "minor",
            "color": {"code": "blue", "red": 30, "green": 50, "blue": 205, "alpha": 1},
            "effectiveTime": "2025-10-24T11:19+08:00",
            "headline": "大风蓝色预警信号",
        }
    ],
}


def test_result_parses_a_real_alert() -> None:
    result = Result.model_validate(PAYLOAD)
    assert result.metadata.tag == "t"
    assert result.metadata.zero_result is False
    assert len(result.alerts) == 1

    alert = result.alerts[0]
    assert alert.id == "202510241119105837988676"
    assert alert.sender_name == "临桂区气象台"
    assert alert.issued_time == "2025-10-24T11:19+08:00"
    assert alert.headline == "大风蓝色预警信号"
    assert alert.effective_time == "2025-10-24T11:19+08:00"


def test_message_type_is_an_object() -> None:
    alert = Result.model_validate(PAYLOAD).alerts[0]
    assert alert.message_type.code == "update"
    assert alert.message_type.supersedes == ["202510181140100706230391"]


def test_event_type_is_an_object() -> None:
    alert = Result.model_validate(PAYLOAD).alerts[0]
    assert alert.event_type.name == "大风"
    assert alert.event_type.code == "1006"


def test_color_has_four_components() -> None:
    alert = Result.model_validate(PAYLOAD).alerts[0]
    assert alert.color.code == "blue"
    assert alert.color.red == 30
    assert alert.color.green == 50
    assert alert.color.blue == 205
    assert alert.color.alpha == 1


def test_optional_fields_are_none_when_missing() -> None:
    """severity 有值，urgency 与 certainty 缺失。

    缺失与零值要能区分：可选字段是 None，不是空串。
    """
    alert = Result.model_validate(PAYLOAD).alerts[0]
    assert alert.severity == "minor"
    assert alert.urgency is None
    assert alert.certainty is None


def test_time_fields_stay_strings() -> None:
    alert = Result.model_validate(PAYLOAD).alerts[0]
    assert isinstance(alert.issued_time, str)
    assert isinstance(alert.effective_time, str)
    assert alert.onset_time == ""
    assert alert.expire_time == ""


def test_empty_alert_list_is_not_null() -> None:
    """没有预警时上游给空列表，metadata.zeroResult 为 true。"""
    result = Result.model_validate({"metadata": {"tag": "t", "zeroResult": True}, "alerts": []})
    assert result.alerts == []
    assert result.metadata.zero_result is True


def test_missing_alerts_key_defaults_to_empty_list() -> None:
    result = Result.model_validate({"metadata": {"tag": "t"}})
    assert result.alerts == []


def test_unknown_fields_are_preserved() -> None:
    """上游新增字段时保留进 model_extra，不丢弃。"""
    alert = Alert.model_validate({"id": "x", "newField": "keep-me"})
    assert alert.model_extra is not None
    assert alert.model_extra["newField"] == "keep-me"


def test_models_can_be_built_without_any_payload() -> None:
    """缺失的非可选字段是零值，不报错。"""
    alert = Alert.model_validate({})
    assert alert.id == ""
    assert alert.message_type == MessageType()
    assert alert.event_type == EventType()
    assert alert.color == Color()
    assert alert.response_types == []


def test_endpoint_value_is_frozen() -> None:
    """端点常量的值在已发布版本里定死。

    TTLPolicy 按值匹配，改值会让用户的 TTL 配置静默失效。
    """
    assert str(Endpoint) == "weatheralert/v1/current"
