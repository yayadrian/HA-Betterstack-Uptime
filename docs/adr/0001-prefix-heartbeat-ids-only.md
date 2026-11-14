# Prefix Heartbeat IDs, leave Monitor IDs bare

Better Stack numbers Monitors and Heartbeats in separate sequences, so the same ID can belong to one of each. Heartbeat unique IDs and device identifiers carry a `heartbeat-` prefix (`heartbeat-123-status`), while Monitor IDs stay unprefixed (`123-status`) as they were before Heartbeats existed. Prefixing both kinds would be more symmetrical, but it would force an entity-registry migration on every existing install for no user benefit, so the asymmetry is deliberate.
