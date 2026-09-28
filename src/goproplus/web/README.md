# web (phase 3, not implemented yet)

Will host a small FastAPI app that reads the same sqlite catalog and the
`data/downloads` tree. It must import only from `goproplus.services` and
`goproplus.infra.database` — never from `goproplus.infra.gopro`.
