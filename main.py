import openai
import functions
from prompts import assistant_instructions
import time
from typing_extensions import override
from openai import AssistantEventHandler
import json

OPENAI_API_KEY="openai-api-key"

client = openai.OpenAI(api_key=OPENAI_API_KEY)

assistant_id, vector_store_id = functions.create_assistant(
    client)

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.snapshot = {}
        self.start_time = time.time()

    @override
    def on_text_created(self, text):
        print("Assistant: ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)
        self.snapshot = snapshot 

    @override
    def on_message_done(self, message) -> None:
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")

#        print(message_content.value)
#        print("\n".join(citations))
    
    @override
    def on_event(self, event):
      if event.event == 'thread.run.requires_action':
        run_id = event.data.id 
        self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
      tool_outputs = []
        
      for tool in data.required_action.submit_tool_outputs.tool_calls:
        if tool.function.name == "get_tires":
            arguments = json.loads(tool.function.arguments)
            width = arguments.get("width", None)
            height = arguments.get("height", None)
            diameter = arguments.get("diameter", None)
            season = arguments.get("season", None)
            vehicle = arguments.get("vehicle", None)
            minimum_price = arguments.get("minimum_price", None)
            maximum_price = arguments.get("maximum_price", None)
            
            output = functions.get_tires(width=width, height=height, diameter=diameter, season=season, vehicle=vehicle, minimum_price=minimum_price, maximum_price=maximum_price)
        tool_outputs.append({"tool_call_id": tool.id, "output": output})
        
      self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
      with client.beta.threads.runs.submit_tool_outputs_stream(
        thread_id=self.current_run.thread_id,
        run_id=self.current_run.id,
        tool_outputs=tool_outputs,
        event_handler=EventHandler(),
      ) as stream:
        stream.until_done()

def chat():
    thread = client.beta.threads.create()
    while True:
        user_message = input("\nUser: ")
        #start_time = time.time()

        message = client.beta.threads.messages.create(
          thread_id=thread.id,
          role="user",
          content=user_message
        )

        with client.beta.threads.runs.stream(
          thread_id=thread.id,
          assistant_id=assistant_id,
          instructions=assistant_instructions,
          event_handler=EventHandler(),
        ) as stream:
          stream.until_done()

chat()
