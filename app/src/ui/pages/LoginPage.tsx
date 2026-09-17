import { signInWithGoogle } from '../../services/auth'

export function LoginPage() {
  return (
    <div className="p-8 text-center flex flex-col items-center gap-4">
      <h1 className="text-2xl font-bold">Sign In</h1>
      <button
        onClick={() => signInWithGoogle()}
        className="bg-[#1B4332] text-white px-4 py-2 rounded"
      >
        Sign in with Google
      </button>
    </div>
  )
}
