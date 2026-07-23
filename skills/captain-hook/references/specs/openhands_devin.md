# Exhaustive OpenHands & Devin Action Interceptors Specification

## 1. Overview & Architecture

OpenHands (formerly All-Hands / Devin OS) provides an event stream runtime where Action Interceptors listen to `Action` events (like `CmdRunAction`, `FileEditAction`) before execution in the sandbox environment.

---

## 2. Configuration & Event Interceptor Contract

- **Config Path**: `config.toml`
- **Interceptors**: Registered Python middleware listening to the event stream.

---

## 3. Event Types & Blocking Semantics

- **`CmdRunAction`**: Intercepts shell execution.
- **`FileEditAction`**: Intercepts file modification.
- **Blocking**: Raising an `ActionRejectionException` or returning a `HookResult(blocked=True)` cancels execution.
