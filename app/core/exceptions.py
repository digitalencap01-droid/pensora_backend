class ContentPipelineError(
    Exception
):
    def __init__(
        self,
        stage: str,
        message: str,
    ) -> None:
        self.stage = stage
        self.message = message

        super().__init__(
            f"{stage}: {message}"
        )
