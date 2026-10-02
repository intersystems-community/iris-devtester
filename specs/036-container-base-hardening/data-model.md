# Data Model: Container Base Hardening

## ContainerCredentials (conceptual)

| Field     | Source                       | Rule                                                       |
| --------- | ---------------------------- | ---------------------------------------------------------- |
| namespace | argument or `IRIS_NAMESPACE` | if not `USER`, matches namespace pattern                   |
| username  | argument or `IRIS_USERNAME`  | validated only when password set; matches username pattern |
| password  | argument or `IRIS_PASSWORD`  | non-empty, no NUL; never logged                            |

## Validation outcomes

| Username | Password                           | Namespace           | Result                               |
| -------- | ---------------------------------- | ------------------- | ------------------------------------ |
| any      | unset                              | valid               | no user created, username ignored    |
| valid    | valid                              | valid               | user created                         |
| invalid  | set                                | any                 | `ValueError` naming `IRIS_USERNAME`  |
| any      | invalid (empty, NUL) with username | any                 | `ValueError`, no value in text       |
| any      | any                                | invalid, not `USER` | `ValueError` naming `IRIS_NAMESPACE` |

## Exec steps

| Step            | Runs when                 | Failure                                   |
| --------------- | ------------------------- | ----------------------------------------- |
| create database | namespace not `USER`      | structured error naming "create database" |
| create user     | username and password set | structured error naming "create user"     |

Each step is a fixed command; values are passed in the environment.

## Licence check result

`rejected` (True), `not rejected` (False), `unreadable` (False plus warning). Other exceptions propagate.

## Label set

`io.iris-devtester.created-by=idt`, `io.iris-devtester.image=<ref>` (omitted when ref unknown).
