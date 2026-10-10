# Infrastructure volontairement non sécurisée — cible Checkov du Test Lab.
# ⚠️  Ne pas appliquer : ces ressources sont faites pour être détectées.

provider "aws" {
  region = "eu-west-3"
}

resource "aws_s3_bucket" "public_data" {
  bucket = "secumerge-lab-public"

  # ACL publique en lecture (volontaire) : CKV_AWS_20.
  acl = "public-read"
}

resource "aws_s3_bucket" "unencrypted" {
  bucket = "secumerge-lab-unencrypted"

  # Pas de chiffrement côté serveur (volontaire) : CKV_AWS_19.
}

resource "aws_security_group" "wide_open" {
  name = "secumerge-lab-wide-open"

  ingress {
    description = "SSH ouvert au monde (volontaire) : CKV_AWS_24."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
