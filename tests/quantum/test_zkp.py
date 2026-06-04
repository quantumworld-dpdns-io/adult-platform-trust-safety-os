"""ZKP tests: age proof, consent proof, identity proof."""

from __future__ import annotations

import time

import pytest

from src.quantum.zkp.age_proof import (
    AgeProof,
    generate_keypair as generate_age_keypair,
    prove_age_over,
    prove_age_range,
    prove_age_under,
    verify_age_proof,
)
from src.quantum.zkp.consent_proof import (
    ConsentProof,
    generate_keypair as generate_consent_keypair,
    prove_consent_given,
    prove_consent_withdrawn,
    verify_consent_proof,
)
from src.quantum.zkp.identity_proof import (
    IdentityCommitment,
    IdentityProof,
    create_identity_commitment,
    generate_keypair as generate_identity_keypair,
    prove_identity_without_pii,
    prove_membership_in_group,
    verify_identity_proof,
)


pytestmark = [pytest.mark.quantum]


class TestAgeProof:
    def test_generate_keypair(self):
        sk, pk = generate_age_keypair()
        assert isinstance(sk, int)
        assert isinstance(pk, int)
        assert sk > 0
        assert pk > 0

    def test_prove_age_over(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_over(birth_hash, sk, pk, current_hash, minimum_age=18)
        assert isinstance(proof, AgeProof)
        assert proof.proof_type == "age_over"
        assert proof.metadata["minimum_age"] == 18

    def test_verify_age_over_proof(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_over(birth_hash, sk, pk, current_hash, minimum_age=18)
        assert verify_age_proof(proof, pk) is True

    def test_verify_age_over_wrong_key(self):
        sk, pk = generate_age_keypair()
        _, wrong_pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_over(birth_hash, sk, pk, current_hash, minimum_age=18)
        assert verify_age_proof(proof, wrong_pk) is False

    def test_prove_age_under(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_under(birth_hash, sk, pk, current_hash, maximum_age=65)
        assert proof.proof_type == "age_under"
        assert proof.metadata["maximum_age"] == 65

    def test_verify_age_under_proof(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_under(birth_hash, sk, pk, current_hash, maximum_age=65)
        assert verify_age_proof(proof, pk) is True

    def test_prove_age_range(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        proof = prove_age_range(birth_hash, sk, pk, current_hash, min_age=18, max_age=65)
        assert proof.proof_type == "age_range"
        assert proof.metadata["min_age"] == 18
        assert proof.metadata["max_age"] == 65

    def test_proofs_non_deterministic(self):
        sk, pk = generate_age_keypair()
        birth_hash = 1234567890
        current_hash = 2345678901
        p1 = prove_age_over(birth_hash, sk, pk, current_hash, 18)
        p2 = prove_age_over(birth_hash, sk, pk, current_hash, 18)
        assert p1.commitment != p2.commitment
        assert p1.challenge != p2.challenge

    def test_proof_commitment_positive(self):
        sk, pk = generate_age_keypair()
        proof = prove_age_over(1, sk, pk, 2, 18)
        assert proof.commitment > 0
        assert proof.challenge > 0


class TestConsentProof:
    def test_generate_keypair(self):
        sk, pk = generate_consent_keypair()
        assert isinstance(sk, int)
        assert isinstance(pk, int)
        assert sk > 0

    def test_prove_consent_given(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_given(
            consent_id="c1",
            consent_type="content",
            private_key=sk,
            public_key=pk,
            timestamp=int(time.time()),
        )
        assert isinstance(proof, ConsentProof)
        assert proof.consent_status == "granted"
        assert proof.consent_type == "content"

    def test_verify_consent_given(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_given(
            consent_id="c1",
            consent_type="content",
            private_key=sk,
            public_key=pk,
            timestamp=int(time.time()),
        )
        assert verify_consent_proof(proof, pk) is True

    def test_prove_consent_withdrawn(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_withdrawn(
            consent_id="c2",
            consent_type="analytics",
            private_key=sk,
            public_key=pk,
            timestamp=int(time.time()),
        )
        assert proof.consent_status == "withdrawn"
        assert proof.consent_type == "analytics"

    def test_verify_consent_withdrawn(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_withdrawn(
            consent_id="c2",
            consent_type="analytics",
            private_key=sk,
            public_key=pk,
            timestamp=int(time.time()),
        )
        assert verify_consent_proof(proof, pk) is True

    def test_consent_proof_wrong_status(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_given(
            consent_id="c3",
            consent_type="marketing",
            private_key=sk,
            public_key=pk,
            timestamp=int(time.time()),
        )
        proof.consent_status = "invalid"
        assert verify_consent_proof(proof, pk) is False

    def test_consent_proof_non_deterministic(self):
        sk, pk = generate_consent_keypair()
        ts = int(time.time())
        p1 = prove_consent_given("c1", "content", sk, pk, ts)
        p2 = prove_consent_given("c1", "content", sk, pk, ts)
        assert p1.commitment != p2.commitment

    def test_consent_proof_metadata(self):
        sk, pk = generate_consent_keypair()
        proof = prove_consent_given("c4", "content", sk, pk, int(time.time()))
        assert "consent_id" in proof.metadata
        assert "consent_hash" in proof.metadata
        assert proof.metadata["consent_id"] == "c4"


class TestIdentityProof:
    def test_generate_keypair(self):
        sk, pk = generate_identity_keypair()
        assert isinstance(sk, int)
        assert isinstance(pk, int)

    def test_create_identity_commitment(self):
        sk, pk = generate_identity_keypair()
        pii = {"name": "John Doe", "dob": "1990-01-01"}
        commitment = create_identity_commitment(sk, pk, pii)
        assert isinstance(commitment, IdentityCommitment)
        assert len(commitment.commitment_hash) == 32
        assert commitment.public_key == pk

    def test_prove_identity_without_pii(self):
        sk, pk = generate_identity_keypair()
        pii = {"name": "Jane Smith", "dob": "1985-06-15"}
        commitment = create_identity_commitment(sk, pk, pii)
        proof = prove_identity_without_pii(sk, pk, commitment)
        assert isinstance(proof, IdentityProof)
        assert proof.proof_type == "identity"

    def test_verify_identity_proof(self):
        sk, pk = generate_identity_keypair()
        pii = {"name": "Test User", "dob": "2000-01-01"}
        commitment = create_identity_commitment(sk, pk, pii)
        proof = prove_identity_without_pii(sk, pk, commitment)
        assert verify_identity_proof(proof, commitment) is True

    def test_verify_identity_wrong_commitment(self):
        sk1, pk1 = generate_identity_keypair()
        sk2, pk2 = generate_identity_keypair()
        commitment1 = create_identity_commitment(sk1, pk1, {"name": "A", "dob": "1990-01-01"})
        commitment2 = create_identity_commitment(sk2, pk2, {"name": "B", "dob": "1985-06-15"})
        proof = prove_identity_without_pii(sk1, pk1, commitment1)
        assert verify_identity_proof(proof, commitment2) is False

    def test_prove_membership_in_group(self):
        sk, pk = generate_identity_keypair()
        members = [pk, 12345, 67890]
        proof = prove_membership_in_group(sk, pk, members, "moderators")
        assert proof.proof_type == "group_membership"
        assert proof.metadata["group_id"] == "moderators"

    def test_commitment_deterministic(self):
        sk, pk = generate_identity_keypair()
        pii = {"name": "Test"}
        c1 = create_identity_commitment(sk, pk, pii, salt=b"\\x01" * 32)
        c2 = create_identity_commitment(sk, pk, pii, salt=b"\\x01" * 32)
        assert c1.commitment_hash == c2.commitment_hash

    def test_commitment_different_salt(self):
        sk, pk = generate_identity_keypair()
        pii = {"name": "Test"}
        c1 = create_identity_commitment(sk, pk, pii, salt=b"\\x01" * 32)
        c2 = create_identity_commitment(sk, pk, pii, salt=b"\\x02" * 32)
        assert c1.commitment_hash != c2.commitment_hash

    def test_identity_proof_non_deterministic(self):
        sk, pk = generate_identity_keypair()
        commitment = create_identity_commitment(sk, pk, {"name": "Test"})
        p1 = prove_identity_without_pii(sk, pk, commitment)
        p2 = prove_identity_without_pii(sk, pk, commitment)
        assert p1.commitment != p2.commitment
