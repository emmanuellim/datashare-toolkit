# Copyright 2020 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Deploy the Datashare UI to Cloud Run."""

import json


def GenerateConfig(context):
  """Generate YAML resource configuration."""
  
  #volumes = [{'name': 'cds-code', 'path': '/cds'}]
  datashare_ui_name_with_tag = "ds-frontend-ui:dev"
  container_tag = context.properties['containerTag']
  cloud_run_deploy_name = context.properties['cloudRunDeployName']
  datashare_ui_name = "ds-frontend-ui"
  gcp_region = context.properties['region']
  delete_timeout = '120s'
  general_timeout = context.properties['timeout']
  cmd = "https://github.com/GoogleCloudPlatform/datashare-toolkit.git"
  git_release_version = "master"
  if context.properties['datashareGitReleaseTag'] != None:
      git_release_version = context.properties['datashareGitReleaseTag']

  steps = [
              { # Clone the Datashare repository only if the ds-frontend-ui:dev is not present
                'name': 'gcr.io/cloud-builders/git',
                'dir': 'ds', # changes the working directory to /workspace/ds/
                'entrypoint': 'bash',
                'args': [ '-c', f'if ! gcloud container images describe gcr.io/$PROJECT_ID/{datashare_ui_name_with_tag}; then ' +
                    'git clone ' + cmd +
                    '; else exit 0; fi'
                    ]
              },
              { # Submit the build configuration to Cloud Build to build the DS UI container image only if the ds-frontend-ui:dev is not present
                  'name': 'gcr.io/google.com/cloudsdktool/cloud-sdk',
                  'dir': 'ds/datashare-toolkit/frontend',
                  'entrypoint': 'bash',
                  'args': [ '-c', f'if ! gcloud container images describe gcr.io/$PROJECT_ID/{datashare_ui_name_with_tag}; then ' +
                      'gcloud builds submit . --config=cloudbuild.yaml ' + 
                      f'--substitutions=TAG_NAME={container_tag}' + 
                      '; else exit 0; fi'
                  ]
              },
              {   # Deploy the container image to Cloud Run
                  'name': 'gcr.io/google.com/cloudsdktool/cloud-sdk',
                  'dir': 'ds/datashare-toolkit/frontend',
                  'args': ['gcloud', 'run',
                            'deploy',
                            context.properties['cloudRunDeployName'],
                            f'--image=gcr.io/$PROJECT_ID/{cloud_run_deploy_name}:{container_tag}', 
                            f'--region={gcp_region}',
                            '--allow-unauthenticated',
                            '--platform=managed'
                          ]
              }
          ]

  if git_release_version != "master":
      git_release = { # Checkout the correct release
                'name': 'gcr.io/cloud-builders/git',
                'dir': 'ds/datashare-toolkit', # changes the working directory to /workspace/ds/datashare-toolkit
                'entrypoint': 'bash',
                'args': [ '-c', 'if ! gcloud container images describe gcr.io/$PROJECT_ID/' + datashare_ui_name_with_tag + '; then ' +
                        'git checkout ' + git_release_version + 
                         '; else exit 0; fi'
                        ]
              }
      steps.insert(1, git_release)

  # include the dependsOn property if we are deploying all the components
  use_runtime_config_waiter = context.properties['useRuntimeConfigWaiter']
  if use_runtime_config_waiter:
      waiter_name = context.properties['waiterName']
      resources = [{
        'name': 'ds-ui-build',
        'action': 'gcp-types/cloudbuild-v1:cloudbuild.projects.builds.create',
        'metadata': {
            'runtimePolicy': ['UPDATE_ALWAYS'],
            'dependsOn': [waiter_name]
        },
        'properties': {
            'steps': steps,
            'timeout': f'{general_timeout}'
        }
        }]
  else:
      resources = [{
      'name': 'ds-ui-build',
      'action': 'gcp-types/cloudbuild-v1:cloudbuild.projects.builds.create',
      'metadata': {
          'runtimePolicy': ['UPDATE_ALWAYS']
      },
      'properties': {
          'steps': steps,
          'timeout': f'{general_timeout}'
      }
    }]

  resources.append({
      'name': 'delete-ui',
      'action': 'gcp-types/cloudbuild-v1:cloudbuild.projects.builds.create',
      'metadata': {
          'dependsOn:': ['ds-ui-build'],
          'runtimePolicy': ['DELETE']
      },
      'properties': {
          'steps': [
              {
                'name': 'gcr.io/google.com/cloudsdktool/cloud-sdk',
                'entrypoint': '/bin/bash',
                'args': ['-c', f'gcloud run services delete {cloud_run_deploy_name} --platform=managed --region={gcp_region} --quiet || exit 0']
              }
          ],
          'timeout': f'{delete_timeout}'
      }
  })
  
  return { 'resources': resources }