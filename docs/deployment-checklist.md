# Deployment checklist

## Before deployment
- [ ] Confirm AWS account access and chosen region.
- [ ] Check current AWS pricing and Free Tier eligibility.
- [ ] Create a billing budget alert.
- [ ] Choose globally unique bucket names; do not enable public access.
- [ ] Build/package Pillow for the Lambda runtime and architecture.

## Resource setup
- [ ] Create source S3 bucket and destination S3 bucket in the same region.
- [ ] Create SQS Standard queue and DLQ; set redrive policy.
- [ ] Add queue policy allowing `s3.amazonaws.com` to call `sqs:SendMessage` only when `aws:SourceArn` is the source bucket ARN.
- [ ] Configure source bucket `ObjectCreated` notification to SQS with prefix `incoming/`.
- [ ] Create Lambda execution role with CloudWatch Logs, `s3:GetObject` on source `incoming/*`, and `s3:PutObject` on destination `thumbnails/*`.
- [ ] Set Lambda environment variables `SOURCE_BUCKET` and `DEST_BUCKET`.
- [ ] Configure SQS event source mapping; begin with batch size 1.
- [ ] Configure visibility timeout to exceed Lambda timeout (AWS guidance commonly recommends at least six times the function timeout for SQS event sources).
- [ ] Confirm DLQ redrive policy and monitoring.

## Evidence to capture
- [ ] S3 source bucket with a sample object in `incoming/`.
- [ ] SQS queue metrics or message processing evidence.
- [ ] Lambda invocation and successful CloudWatch log.
- [ ] Destination bucket containing the thumbnail.
- [ ] One failure-handling test and DLQ evidence, if safely tested.
- [ ] Architecture diagram and README in the public GitHub repository.

## Cleanup
- [ ] Download evidence and commit it to the repository.
- [ ] Empty and delete test buckets, queues, and Lambda resources if they are no longer needed.
- [ ] Check billing dashboard after cleanup.
