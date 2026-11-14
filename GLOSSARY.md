# Better Stack Uptime

A Home Assistant integration that mirrors the state of a Better Stack Uptime account's checks as Home Assistant devices and entities.

## Language

### Checks

**Check**:
Anything in Better Stack Uptime that has an up/down status: either a Monitor or a Heartbeat.
_Avoid_: Monitor (when meaning both kinds), probe

**Monitor**:
A Check where Better Stack actively probes a target (a URL, host, port or similar) on a schedule.
_Avoid_: Check (when meaning only this kind)

**Heartbeat**:
A Check where Better Stack waits for an external job to call it, and raises an incident when a call is late.
_Avoid_: Cron monitor, push monitor, ping

**Heartbeat URL**:
The secret address a job calls to report a Heartbeat; whoever holds it can report on the Heartbeat's behalf.
_Avoid_: Ping URL

**Period**:
How often a Heartbeat expects to be called.
_Avoid_: Interval, frequency

**Grace**:
How late a Heartbeat call may be before Better Stack treats it as missed.
_Avoid_: Tolerance, timeout

### Status

**Status**:
Better Stack's current verdict on a Check: one of up, down, pending, paused, maintenance or validating.
_Avoid_: State (Home Assistant's term for an entity's value)

**Up**:
A Check is Up when its Status is up or validating.
_Avoid_: Online, healthy

**Validating**:
The Status of a Check that is passing again while Better Stack waits to resolve its open incident.
_Avoid_: Recovering
