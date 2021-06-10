#!/usr/bin/env python3
import os

#from aws_cdk import core as cdk
from aws_cdk import core
from docker_pipeline.docker_pipeline import DockerPipelineConstruct
from terraform_pipeline.terraform_pipeline_stack import TerraformPipelineStack

app = core.App()
name = app.node.try_get_context("name")
container_stack = core.Stack(scope=app,id=f"{name}-container-stack")
terraform_stack = core.Stack(scope=app,id=f"{name}-stack")


docker_stack=DockerPipelineConstruct(
    scope=container_stack,
    id=f"{name}-docker-pipeline"
)  

terraform_pipeline_stack=TerraformPipelineStack(
    scope=terraform_stack, 
    id=f"{name}-terraform-pipeline",
    ecr_repository=docker_stack.container_repository
)

app.synth()
