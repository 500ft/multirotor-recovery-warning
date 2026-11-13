#!/usr/bin/env python3
"""Minimal dependency-free rigid-body attitude integration kernel."""

from __future__ import annotations

from math import sqrt

Vector3 = tuple[float, float, float]
Quaternion = tuple[float, float, float, float]


def cross(a: Vector3, b: Vector3) -> Vector3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def quaternion_norm(q: Quaternion) -> float:
    return sqrt(sum(value * value for value in q))


def normalize_quaternion(q: Quaternion) -> Quaternion:
    norm = quaternion_norm(q)
    if norm == 0:
        raise ValueError("zero quaternion cannot be normalized")
    return tuple(value / norm for value in q)  # type: ignore[return-value]


def quaternion_multiply(a: Quaternion, b: Quaternion) -> Quaternion:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def angular_acceleration(
    omega: Vector3, torque: Vector3, inertia_diagonal: Vector3
) -> Vector3:
    if min(inertia_diagonal) <= 0:
        raise ValueError("inertia values must be positive")
    inertia_omega = tuple(
        inertia_diagonal[index] * omega[index] for index in range(3)
    )
    gyroscopic = cross(omega, inertia_omega)  # type: ignore[arg-type]
    return tuple(
        (torque[index] - gyroscopic[index]) / inertia_diagonal[index]
        for index in range(3)
    )  # type: ignore[return-value]


def step(
    quaternion: Quaternion,
    omega: Vector3,
    torque: Vector3,
    inertia_diagonal: Vector3,
    dt: float,
) -> tuple[Quaternion, Vector3]:
    alpha = angular_acceleration(omega, torque, inertia_diagonal)
    next_omega = tuple(
        omega[index] + alpha[index] * dt for index in range(3)
    )  # type: ignore[assignment]
    omega_quaternion: Quaternion = (0.0, *next_omega)
    q_dot = quaternion_multiply(quaternion, omega_quaternion)
    next_quaternion = normalize_quaternion(
        tuple(
            quaternion[index] + 0.5 * q_dot[index] * dt for index in range(4)
        )  # type: ignore[arg-type]
    )
    return next_quaternion, next_omega
