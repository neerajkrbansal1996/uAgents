"""Agent Envelope."""

import base64
import hashlib
import struct
from typing import Callable, Optional

from pydantic import UUID4, BaseModel, ConfigDict

from uagents.crypto import Identity
from uagents.dispatch import JsonStr


class Envelope(BaseModel):
    """
    Represents an envelope for message communication between agents.

    Attributes:
        version (int): The envelope version.
        sender (str): The sender's address.
        target (str): The target's address.
        session (UUID4): The session UUID that persists for back-and-forth
        dialogues between agents.
        schema_digest (str): The schema digest for the enclosed message.
        protocol_digest (Optional[str]): The digest of the protocol associated with the message
        (optional).
        payload (Optional[str]): The encoded message payload of the envelope (optional).
        expires (Optional[int]): The expiration timestamp (optional).
        nonce (Optional[int]): The nonce value (optional).
        signature (Optional[str]): The envelope signature (optional).
    """

    version: int
    sender: str
    target: str
    session: UUID4
    schema_digest: str
    protocol_digest: Optional[str] = None
    payload: Optional[str] = None
    expires: Optional[int] = None
    nonce: Optional[int] = None
    signature: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    def encode_payload(self, value: JsonStr):
        """
        Encode the payload value and store it in the envelope.

        Args:
            value (JsonStr): The payload value to be encoded.
        """
        self.payload = base64.b64encode(value.encode()).decode()

    def decode_payload(self) -> str:
        """
        Decode and retrieve the payload value from the envelope.

        Returns:
            str: The decoded payload value, or '' if payload is not present.
        """
        if self.payload is None:
            return ""

        return base64.b64decode(self.payload).decode()

    def sign(self, signing_fn: Callable):
        """
        Sign the envelope using the provided signing function.

        Args:
            signing_fn (callback): The callback used for signing.
        """
        try:
            self.signature = signing_fn(self._digest())
        except Exception as err:
            raise ValueError(f"Failed to sign envelope: {err}") from err

    def verify(self) -> bool:
        """
        Verify the envelope's signature.

        Returns:
            bool: True if the signature is valid.

        Raises:
            ValueError: If the signature is missing.
            ecdsa.BadSignatureError: If the signature is invalid.
        """
        if self.signature is None:
            raise ValueError("Envelope signature is missing")
        return Identity.verify_digest(self.sender, self._digest(), self.signature)

    def _digest(self) -> bytes:
        """
        Compute the digest of the envelope's content.

        Returns:
            bytes: The computed digest.
        """
        hasher = hashlib.sha256()
        hasher.update(self.sender.encode())
        hasher.update(self.target.encode())
        hasher.update(str(self.session).encode())
        hasher.update(self.schema_digest.encode())
        if self.payload is not None:
            hasher.update(self.payload.encode())
        if self.expires is not None:
            hasher.update(struct.pack(">Q", self.expires))
        if self.nonce is not None:
            hasher.update(struct.pack(">Q", self.nonce))
        return hasher.digest()
