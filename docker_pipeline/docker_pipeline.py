from aws_cdk import (
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as codepipeline_actions,
    aws_ecr as ecr,
    aws_iam as iam,
    core
)    


class DockerPipelineConstruct(core.Construct):

    def __init__(
        self, 
        scope: core.Construct, 
        id: str,
    ) -> None:
        super().__init__(scope=scope, id=id)
        account = scope.account
        region = scope.region        
        name = scope.node.try_get_context("name")
        # ECR repositories
        self.container_repository = ecr.Repository(
            scope=self,
            id=f"{name}-container",
            repository_name=f"{name}-container"
        )
        # Repo for Application
        codecommit_repo = codecommit.Repository(
            scope=self, 
            id=f"{name}-container-git",
            repository_name=f"{name}-container",
            description=f"Docker custom image code"
        )

        pipeline = codepipeline.Pipeline(
            scope=self, 
            id=f"{name}-container-pipeline",
            pipeline_name=f"{name}-container-pipeline"
        )


       
       
        source_output = codepipeline.Artifact()
        docker_output = codepipeline.Artifact(artifact_name="Docker")

        buildspec_docker = codebuild.BuildSpec.from_source_filename("buildspec.yml")

        docker_build = codebuild.PipelineProject(
            scope=self,
            id=f"DockerBuild",
            environment=dict(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_3,
                privileged=True),
            environment_variables={
                'REPO_ECR': codebuild.BuildEnvironmentVariable(
                    value=self.container_repository.repository_uri),
            },
            build_spec=buildspec_docker
        )

        self.container_repository.grant_pull_push(docker_build)
        docker_build.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ecr:BatchCheckLayerAvailability", "ecr:GetDownloadUrlForLayer", "ecr:BatchGetImage"],
            resources=[f"arn:aws:ecr:{region}:{account}:repository/*"],))

        source_action = codepipeline_actions.CodeCommitSourceAction(
            action_name="CodeCommit_Source",
            repository=codecommit_repo,
            output=source_output,
            branch="main"
        )

        pipeline.add_stage(
            stage_name="Source",
            actions=[source_action]
        )

        # Stages in CodePipeline
        pipeline.add_stage(
            stage_name="DockerBuild",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name=f"DockerBuild_and_Push_ECR",
                    project=docker_build,
                    input=source_output,
                    outputs=[docker_output])
            ]
        )