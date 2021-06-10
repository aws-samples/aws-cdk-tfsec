FROM amazonlinux:latest
LABEL maintainer="César Prieto Ballester (cesarpb@amazon.es), Bruno Augusto Bardelli (bardbrun@amazon.es)"

ENV TERRAFORM_VERSION 0.15.5
ENV TFSEC_VERSION 0.39.42


# install awscli

RUN yum update -y  && yum install -y \
	ca-certificates \
  curl \
	less \
	python3 \
  unzip \
	py-pip \
	&& rm -rf /var/cache/yum/* \
  && pip3 install pip --upgrade \
  && pip3 install awscli

# Install Terraform
RUN cd /usr/local/bin && \
    curl https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip -o terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Install tfsec
RUN curl -Lso tfsec https://github.com/tfsec/tfsec/releases/download/v${TFSEC_VERSION}/tfsec-linux-amd64
RUN chmod +x tfsec && mv tfsec /usr/local/bin/
