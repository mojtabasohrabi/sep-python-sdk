# Security policy

## Reporting a vulnerability

Please do **not** open a public issue for a security problem. Use GitHub's private
vulnerability reporting ("Security" tab → "Report a vulnerability") on this repository.
You will get an answer within a few days.

## Scope

This package talks to a payment gateway, so the following are treated as security bugs:

- a way to make `verify_callback` succeed without the gateway confirming the money;
- leaking a payment token, receipt, card hash or masked card number into logs or exceptions;
- accepting a response that should have been refused (wrong receipt, wrong terminal, wrong amount).

## Supported versions

The latest minor release receives fixes.
