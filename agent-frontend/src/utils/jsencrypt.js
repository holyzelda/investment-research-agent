import JSEncrypt from 'jsencrypt'

const publicKey = `MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC13hBhPvst9Qi23eIli+4EHYX6
jz9rCF7vQXXFA3DbTNHOd39OtpWHgF1ApLl0FaDceETLJj1ZknUVFmzyHIeIBw4j
x97x7kduvKeKRcjb2XCWhCfj4J2q7n1qlT4BHjargD5Ev7d8bBbKiKYbaCQvMzCP
HyAybzVzqAgKoZ4uJwIDAQAB`

export function encrypt(value) {
  const encryptor = new JSEncrypt()
  encryptor.setPublicKey(publicKey)
  return encryptor.encrypt(value)
}
