# Labels Contract

| Label                          | Value                                                             |
| ------------------------------ | ----------------------------------------------------------------- |
| `io.iris-devtester.created-by` | `idt`                                                             |
| `io.iris-devtester.image`      | image reference used to create the container (omitted if unknown) |

Applied to containers created by `idt container up` and by `IRISContainerManager._create_with_docker_sdk`. Feature 035 reads these labels to decide which containers it may remove. The existing `iris-devtester.config.source` key is unrelated and unchanged.
