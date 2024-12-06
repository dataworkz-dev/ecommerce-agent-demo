import streamlit as st
import os
import requests
import json

# App title
st.set_page_config(page_title="Dataworkz Agent Chatbot")

# Replicate Credentials
with st.sidebar:
    st.title('Dataworkz Agent Chatbot')
    st.write('This chatbot is an interface to an agent created using Dataworkz (https://www.dataworkz.com).')

token = st.secrets['token']
if token:
    st.sidebar.success('Token provided')
systemId = st.secrets.systemId
llmId = st.secrets.llmId
service = st.secrets.service
st.sidebar.write('Connecting to ', service)
agentSpec = st.secrets.agent_spec
contextMsg = st.secrets.context_message
urlTemplate = service + "/api/qna/v1/systems/" + systemId + "/call-agent?llmProviderId=" + llmId + "&userText="; 
headers = {
        "Authorization": "SSWS " + token,
        "Content-Type": "application/json"
}

# Function to simplify JSON by removing specific keys
def simplify_json(data):
    if isinstance(data, dict):
        simplified = {}
        for key, value in data.items():
            if not key.startswith("__DW__") and key not in {"ref", "id", "instanceId", "startMillis", "endMillis", "durationMillis", "status", "statusMessage"}:
                simplified[key] = simplify_json(value)
        return simplified
    elif isinstance(data, list):
        return [simplify_json(item) for item in data]
    return data

new_user_message = False

def show_probe():
    with st.expander("View Probe", expanded=False):
        # Assuming the last response is the one to simplify
        if "last_response" in st.session_state:
            st.json(st.session_state["last_response"], expanded=False)
        else:
            st.write("No data available.")

# Button in the sidebar to show simplified JSON
st.sidebar.button("Show Probe Viewer", on_click=show_probe)

with open(agentSpec) as json_file:
    print(json_file)
    json_data = json.load(json_file)

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]
    new_user_message = False
st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

# Function for generating LLaMA2 response. Refactored from https://github.com/a16z-infra/llama2-chatbot
def generate_dw_agent_response(userText):
    string_dialogue = []
    if contextMsg:
        string_dialogue.append({ "by": "USER", "text": contextMsg })
    for dict_message in st.session_state.messages:
        if dict_message["role"] == "user":
            string_dialogue.append({ "by": "USER", "text": dict_message["content"] })
        else:
            string_dialogue.append({ "by": "AI", "text": dict_message["content"] })
    json_data["conversationHistory"] = string_dialogue;
    print(json_data)
    # Call DW Agent
    print(urlTemplate + userText)
    response = requests.post(urlTemplate + userText, json=json_data, headers=headers)
    print(response)
    if response.status_code == 200:
        resJson = response.json()
        print(resJson)
        output = resJson 
        # ["answer"]
    else:
        output = "I am sorry but I was unable to get a response."
    return output

# User-provided prompt
if prompt := st.chat_input(disabled=not token):
    new_user_message = True
    with st.chat_message("user"):
        st.write(prompt)

# Generate a new response if last message is not from assistant
if new_user_message: # st.session_state.messages[-1]["role"] != "assistant":
    new_user_message = False

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = generate_dw_agent_response(prompt)
            st.session_state["last_response"] = simplify_json(response.get("probe", {}))
            placeholder = st.empty()
            full_response = ''
            for item in response["answer"]:
                full_response += item
            full_response = full_response.replace('\\n', '\n')
            print("full_response", full_response)
            placeholder.write(full_response)
    st.session_state.messages.append({"role": "user", "content": prompt})
    message = {"role": "assistant", "content": full_response}
    st.session_state.messages.append(message)
