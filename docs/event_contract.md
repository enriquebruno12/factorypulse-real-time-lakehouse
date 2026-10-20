# FactoryPulse Event Contract

**Status:** Draft for review  
**Author:** _Add your name_  
**Date:** _Add the date_

## Purpose

Define what each machine event means and which values are valid before building the simulator. Compare each proposed business rule with the constraints currently implemented in PostgreSQL. This document is a working template; fill it in and review the decisions before changing the SQL or writing the generator.

## Event definitions

### MACHINE_STARTED

- **What happened on the factory floor?** _Write here._
- **Should `order_id` be required? Why?** _Write here._
- **What does `units_produced` mean? Which values are valid?** _Write here._
- **Does the current SQL enforce your rule? Name the constraint or gap.** _Write here._

### MACHINE_STOPPED

- **What happened on the factory floor?** _Write here._
- **Should `order_id` be required? Why?** _Write here._
- **What does `units_produced` mean? Which values are valid?** _Write here._
- **Does the current SQL enforce your rule? Name the constraint or gap.** _Write here._

### PRODUCTION_REPORTED

- **What happened on the factory floor?** _Write here._
- **Should `order_id` be required? Why?** _Write here._
- **What does `units_produced` mean? Which values are valid?** _Write here._
- **Does the current SQL enforce your rule? Name the constraint or gap.** _Write here._

### FAULT_DETECTED

- **What happened on the factory floor?** _Write here._
- **Should `order_id` be required? Why?** _Write here._
- **What does `units_produced` mean? Which values are valid?** _Write here._
- **Does the current SQL enforce your rule? Name the constraint or gap.** _Write here._

## Open questions and assumptions

### Rules I need to clarify

1. _Write here._
2. _Write here._

### Assumptions to confirm

1. _Write here._
2. _Write here._

## Source tables

- [machines](../sql/001_create_machines.sql)
- [production_orders](../sql/002_create_production_orders.sql)
- [machine_events](../sql/003_create_machine_events.sql)
