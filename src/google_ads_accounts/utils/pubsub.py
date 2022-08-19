# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for sending messages to Pub/sub."""
import json
from typing import Any, Dict, List
from google.cloud import pubsub_v1


def send_dict_to_pubsub(message_dict: Dict[str, Any],
                        topic: str,
                        gcp_project: str) -> None:
    """Push the dictionary to pubsub.

    Args:
        message_dict: the message as a dictionary to push to pubsub
        topic: the name of the topic to publish the message to
        gcp_project: the Google Cloud Project with the pub/sub topic in
    """

    publisher = pubsub_v1.PublisherClient()
    # The `topic_path` method creates a fully qualified identifier
    # in the form `projects/{project_id}/topics/{topic_id}`
    topic_path = publisher.topic_path(gcp_project, topic)
    message_str = json.dumps(message_dict)
    # Data must be a bytestring
    data = message_str.encode('utf-8')
    publisher.publish(topic_path, data)


def send_dicts_to_pubsub(messages: List[Dict[str, Any]],
                         topic: str,
                         gcp_project: str) -> None:
    """Push each message in the list to pubsub.

    Args:
        messages: a list of messages as dicts to push to pubsub
        topic: the name of the topic to publish the message to
        gcp_project: the Google Cloud Project with the pub/sub topic in
    """
    for message in messages:
        send_dict_to_pubsub(
            message_dict=message, topic=topic, gcp_project=gcp_project)
