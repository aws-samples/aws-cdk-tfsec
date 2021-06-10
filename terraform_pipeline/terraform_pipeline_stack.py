
from aws_cdk import (
    aws_codecommit as codecommit,
    aws_codepipeline as codepipeline,
    aws_codebuild as codebuild,
    aws_codepipeline_actions as codepipeline_actions,
    pipelines as pipelines,
    aws_ecr as ecr,
    aws_iam as iam,
    core
)

from docker_pipeline.docker_pipeline import DockerPipelineConstruct

class TerraformPipelineStack(core.Construct) :

    def __init__(
        self, 
        scope: core.Construct, 
        id: str,
        ecr_repository
    ) -> None:
        super().__init__(scope=scope, id=id)
        account = scope.account
        region = scope.region        
        name = scope.node.try_get_context("name")
        
        # Terraform codecommit Repo
        codecommit_repo = codecommit.Repository(
            scope=self,
            id=f"{name}-code",
            repository_name=f"{name}",
            description=f"Terraform code"
        )

        pipeline = codepipeline.Pipeline(
            scope=self,
            id=f"{name}-pipeline",
            pipeline_name=f"{name}"
        )    

        source_output = codepipeline.Artifact()

        buildspec_tfsec = codebuild.BuildSpec.from_source_filename("buildspec_tfsec.yml")

        tfsec = codebuild.PipelineProject(
            scope=self,
            id=f"tfsec",
            environment=dict(
                build_image=codebuild.LinuxBuildImage.from_ecr_repository(ecr_repository),
                privileged=True,
                compute_type=codebuild.ComputeType.SMALL),
                build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",
                    "env": {
                        "exported-variables": [
                              "BuildID",
                              "BuildTag",
                              "Region",
                              "checks_failed"
                        ]
                    },
                    "phases": { 
                    "pre_build": {
                        "commands": [
                            "echo Executing tfsec",
                            "mkdir -p reports/tfsec/"
                        ]
                      },
                    "build": {
                        "commands": [
                            "tfsec -s code_security_checks/tfsec/tfsec.yml .",
                            "tfsec -s code_security_checks/tfsec/tfsec.yml . --format junit > reports/tfsec/report.xml",
                            "num_errors=`tfsec -s --config-file code_security_checks/tfsec/tfsec.yml . |  grep ERROR | wc -l`",
                            "export BuildID=`echo $CODEBUILD_BUILD_ID | cut -d: -f1`",
                            "export BuildTag=`echo $CODEBUILD_BUILD_ID | cut -d: -f2`",
                            "export Region=$AWS_REGION",
                            "export checks_failed=$num_errors"
                        ]
                      }
                     },
                     "reports": {
                        "tfsec-reports": {
                            "files": [
                               "reports/tfsec/*.xml"
                            ],
                            "file-format": "JUNITXML"
                        }  
                    }
                })
        )

        terraform_plan = codebuild.PipelineProject(
            scope=self,
            id=f"terraform_plan",
            environment=dict(
                build_image=codebuild.LinuxBuildImage.from_ecr_repository(ecr_repository),
                privileged=True,
                compute_type=codebuild.ComputeType.SMALL),
                build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",
                    "env": {
                        "exported-variables": [
                              "BuildID",
                              "BuildTag",
                              "Region"
                        ]
                    },
                    "phases": { 
                    "build": {
                        "commands": [
                            "terraform init",
                            "terraform plan",
                            "export BuildID=`echo $CODEBUILD_BUILD_ID | cut -d: -f1`",
                            "export BuildTag=`echo $CODEBUILD_BUILD_ID | cut -d: -f2`",
                            "export Region=$AWS_REGION",
                            "echo $"
                        ]
                     }
                    }
                })
            )
        terraform_apply = codebuild.PipelineProject(
            scope=self,
            id=f"terraform_apply",
            environment=dict(
                build_image=codebuild.LinuxBuildImage.from_ecr_repository(ecr_repository),
                privileged=True,
                compute_type=codebuild.ComputeType.SMALL),
                build_spec=codebuild.BuildSpec.from_object({
                    "version": "0.2",             
                    "phases": { 
                    "build": {
                        "commands": [
                            "terraform init",
                            "terraform apply -auto-approve"
                        ]
                     }
                    }
                })
            )


        terraform_plan.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ec2:*"],
            resources=[f"*"],))

        terraform_apply.add_to_role_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["ec2:*"],
            resources=[f"*"],))  


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
            stage_name="tfsec_analysis",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    action_name=f"tfec_security",
                    project=tfsec,
                    input=source_output,
                    variables_namespace="TFSEC"
                )
            ]
        )
        pipeline.add_stage(
            stage_name="Terraform_Stages",
            actions=[
                codepipeline_actions.ManualApprovalAction(
                    action_name = f"Terraform_Security_Analysis_Manual_Review",
                    additional_information = "tfsec errors found: #{TFSEC.checks_failed}",
                    external_entity_link = "https://#{TFSEC.Region}.console.aws.amazon.com/codesuite/codebuild/"+core.Stack.of(self).account+"/projects/#{TFSEC.BuildID}/build/#{TFSEC.BuildID}%3A#{TFSEC.BuildTag}/?region=#{TFSEC.Region}",
                    run_order = 1
                ),
                codepipeline_actions.CodeBuildAction(
                    action_name=f"Terraform_Plan",
                    project=terraform_plan,
                    input=source_output,
                    run_order = 2,
                    variables_namespace="TERRAFORM"
                ),
                codepipeline_actions.ManualApprovalAction(
                    action_name = f"Terraform_Plan_Manual_Review",
                    additional_information = "Terraform plan review",
                    external_entity_link = "https://#{TERRAFORM.Region}.console.aws.amazon.com/codesuite/codebuild/"+core.Stack.of(self).account+"/projects/#{TERRAFORM.BuildID}/build/#{TERRAFORM.BuildID}%3A#{TERRAFORM.BuildTag}/?region=#{TERRAFORM.Region}",
                    run_order = 3
                ),
                
                codepipeline_actions.CodeBuildAction(
                    action_name=f"Terraform_Apply",
                    project=terraform_apply,
                    input=source_output,
                    run_order = 4
                ),
            ]
        )