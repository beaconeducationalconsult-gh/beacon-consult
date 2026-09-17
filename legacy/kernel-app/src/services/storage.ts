import { ref, uploadBytes, getDownloadURL } from 'firebase/storage'
import { storage } from './firebase'

export async function uploadDocument(
  blob: Blob,
  schoolId: string,
  filename: string
): Promise<string> {
  const storageRef = ref(storage, `schools/${schoolId}/documents/${filename}`)
  await uploadBytes(storageRef, blob)
  return getDownloadURL(storageRef)
}
