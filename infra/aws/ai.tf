resource "aws_iam_role_policy" "bedrock_advisory" {
  name = "${local.name}-bedrock-readonly"
  role = aws_iam_role.task.id
  policy = jsonencode({Version="2012-10-17",Statement=[{
    Effect="Allow",Action=["bedrock:InvokeModel"],Resource=[var.bedrock_model_arn]
  }]})
}
