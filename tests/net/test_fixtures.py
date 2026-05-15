from __future__ import annotations

from p2p_tetris.common import PlayerId
from p2p_tetris.net import ClientHello, MessageCodec
from tests.fixtures.net.helpers import FakeTransport, LossyDatagramLink


def test_fake_transport_and_lossy_link_are_deterministic() -> None:
    message = ClientHello(PlayerId("p1"))
    transport = FakeTransport()
    link = LossyDatagramLink(drop_every=2, duplicate_every=3)

    transport.queue_inbound(message)
    assert transport.poll()[0].message == message
    assert len(link.transmit(message)) == 1
    assert link.transmit(message) == []
    duplicated = link.transmit(message)
    assert len(duplicated) == 2
    assert MessageCodec().decode(duplicated[0]) == message
