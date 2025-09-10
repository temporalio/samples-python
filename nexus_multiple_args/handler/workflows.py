from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nexus_multiple_args.service import HelloInput, HelloOutput, Language


# This is the workflow that is started by the `hello` nexus operation.
# It demonstrates handling multiple arguments passed from the Nexus service.
@workflow.defn
class HelloHandlerWorkflow:
    @workflow.run
    async def run(self, name: str, language: Language) -> HelloOutput:
        """
        Handle the hello workflow with multiple arguments.
        
        This method receives the individual arguments (name and language) 
        that were unpacked from the HelloInput in the service handler.
        """
        if language == Language.EN:
            message = f"Hello {name} 👋"
        elif language == Language.FR:
            message = f"Bonjour {name} 👋"
        elif language == Language.DE:
            message = f"Hallo {name} 👋"
        elif language == Language.ES:
            message = f"¡Hola! {name} 👋"
        elif language == Language.TR:
            message = f"Merhaba {name} 👋"
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        return HelloOutput(message=message)