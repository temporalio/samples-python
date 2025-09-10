from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nexus_multiple_args.service import HelloOutput


# This is the workflow that is started by the `hello` nexus operation.
# It demonstrates handling multiple arguments passed from the Nexus service.
@workflow.defn
class HelloHandlerWorkflow:
    @workflow.run
    async def run(self, name: str, language: str) -> HelloOutput:
        """
        Handle the hello workflow with multiple arguments.

        This method receives the individual arguments (name and language)
        that were unpacked from the HelloInput in the service handler.
        """
        if language == "en":
            message = f"Hello {name} 👋"
        elif language == "fr":
            message = f"Bonjour {name} 👋"
        elif language == "de":
            message = f"Hallo {name} 👋"
        elif language == "es":
            message = f"¡Hola! {name} 👋"
        elif language == "tr":
            message = f"Merhaba {name} 👋"
        else:
            raise ValueError(f"Unsupported language: {language}")

        return HelloOutput(message=message)
