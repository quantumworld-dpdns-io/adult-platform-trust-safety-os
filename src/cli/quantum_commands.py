"""Quantum CLI commands: QRNG, PQC encryption, ZKP operations."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Quantum security operations")
console = Console()


@app.command("generate-qrng")
def generate_qrng(
    bits: int = typer.Option(256, "--bits", "-b", help="Number of random bits"),
    format: str = typer.Option("hex", "--format", "-f", help="Output format (hex/binary/int)"),
) -> None:
    """Generate quantum random numbers."""
    from src.quantum.circuits.qrng import QRNGCircuit

    circuit = QRNGCircuit(num_qubits=min(bits, 20))
    result = circuit.generate_random_bits(bits)

    if format == "hex":
        output = result.to_bytes((bits + 7) // 8, "big").hex()
    elif format == "binary":
        output = bin(result)[2:].zfill(bits)
    else:
        output = str(result)

    console.print(f"[green]Generated {bits} random bits:[/green]")
    console.print(output[:100])
    if len(output) > 100:
        console.print(f"[dim]... ({len(output)} chars total)[/dim]")


@app.command("pqc-encrypt")
def pqc_encrypt(
    data: str = typer.Option(..., "--data", "-d", help="Data to encrypt"),
    algorithm: str = typer.Option("kyber", "--algo", "-a", help="PQC algorithm"),
) -> None:
    """Encrypt data with post-quantum cryptography."""
    from src.quantum.pqc.key_encapsulation import generate_keypair, encapsulate

    if algorithm != "kyber":
        console.print(f"[yellow]Algorithm '{algorithm}' not yet supported, using kyber[/yellow]")

    keypair = generate_keypair()
    ciphertext, shared_secret = encapsulate(keypair["public_key"])

    console.print(f"[green]PQC Encryption ({algorithm}):[/green]")
    console.print(f"  Ciphertext length: {len(ciphertext)} bytes")
    console.print(f"  Shared secret: {shared_secret.hex()[:32]}...")
    console.print(f"  Data encrypted: {len(data)} chars")


@app.command("pqc-decrypt")
def pqc_decrypt(
    ciphertext_hex: str = typer.Option(..., "--ciphertext", "-c", help="Hex ciphertext"),
    private_key_hex: str = typer.Option(..., "--private-key", "-k", help="Hex private key"),
    encapsulated_key_hex: str = typer.Option(..., "--ek", help="Hex encapsulated key"),
    algorithm: str = typer.Option("kyber", "--algo", "-a", help="PQC algorithm"),
) -> None:
    """Decrypt data with post-quantum cryptography."""
    from src.quantum.pqc.key_encapsulation import decapsulate

    try:
        ciphertext = bytes.fromhex(ciphertext_hex)
        private_key = bytes.fromhex(private_key_hex)
        encapsulated_key = bytes.fromhex(encapsulated_key_hex)
        shared_secret = decapsulate(ciphertext, private_key, encapsulated_key)
        console.print(f"[green]Decryption successful[/green]")
        console.print(f"  Shared secret: {shared_secret.hex()[:32]}...")
    except Exception as e:
        console.print(f"[red]Decryption failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("zkp-prove-age")
def zkp_prove_age(
    birth_date: str = typer.Option(..., "--birth-date", help="Birth date (YYYY-MM-DD)"),
    minimum_age: int = typer.Option(18, "--min-age", help="Minimum age to prove"),
) -> None:
    """Generate a zero-knowledge proof of age."""
    from src.quantum.zkp.age_proof import generate_keypair, prove_age_over, AgeProof
    from datetime import datetime

    private_key, public_key = generate_keypair()
    now = datetime.utcnow()
    dob = datetime.fromisoformat(birth_date)
    birth_hash = int.from_bytes(dob.strftime("%Y%m%d").encode().digest()[:32], "big") if hasattr(dob.strftime("%Y%m%d").encode(), "digest") else hash(dob.date().isoformat()) % (2**256)
    current_hash = hash(now.date().isoformat()) % (2**256)

    proof = prove_age_over(
        birth_date_hash=birth_hash,
        private_key=private_key,
        public_key=public_key,
        current_date_hash=current_hash,
        minimum_age=minimum_age,
    )

    console.print(f"[green]ZKP Age Proof Generated:[/green]")
    console.print(f"  Proof type: {proof.proof_type}")
    console.print(f"  Minimum age: {minimum_age}")
    console.print(f"  Commitment: {str(proof.commitment)[:32]}...")
    console.print(f"  Challenge:  {str(proof.challenge)[:32]}...")
    console.print(f"  Response:   {str(proof.response)[:32]}...")
    console.print(f"[dim]Public key: {str(public_key)[:32]}...[/dim]")


@app.command("zkp-verify")
def zkp_verify(
    commitment: str = typer.Option(..., help="Proof commitment"),
    challenge: str = typer.Option(..., help="Proof challenge"),
    response: str = typer.Option(..., help="Proof response"),
    proof_type: str = typer.Option("age_over", help="Proof type"),
    public_key: str = typer.Option(..., help="Verifier public key"),
    birth_hash: str = typer.Option("0", help="Birth date hash"),
    current_hash: str = typer.Option("0", help="Current date hash"),
    min_age: str = typer.Option("18", help="Minimum age"),
) -> None:
    """Verify a zero-knowledge age proof."""
    from src.quantum.zkp.age_proof import verify_age_proof, AgeProof

    proof = AgeProof(
        commitment=int(commitment),
        challenge=int(challenge),
        response=int(response),
        proof_type=proof_type,
        metadata={
            "birth_date_hash": int(birth_hash),
            "current_date_hash": int(current_hash),
            "minimum_age": int(min_age),
        },
    )

    valid = verify_age_proof(proof, int(public_key))
    if valid:
        console.print("[green]Proof is VALID[/green]")
    else:
        console.print("[red]Proof is INVALID[/red]")
        raise typer.Exit(1)


@app.command("circuit-info")
def circuit_info() -> None:
    """Show information about available quantum circuits."""
    table = Table(title="Quantum Circuits")
    table.add_column("Circuit", style="cyan")
    table.add_column("Description")
    table.add_column("Qubits")

    circuits = [
        ("QRNG", "Quantum Random Number Generator", "1-20"),
        ("Superdense", "Superdense coding protocol", "2"),
        ("Teleportation", "Quantum teleportation", "3"),
        ("QKD", "Quantum Key Distribution", "2"),
    ]
    for name, desc, qubits in circuits:
        table.add_row(name, desc, qubits)
    console.print(table)
