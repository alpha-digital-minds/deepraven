<template>
  <div id="login-screen">
    <div class="login-card">
      <div class="login-logo">
        <img src="/assets/logo.png" alt="DeepRaven" />
      </div>
      <h2 id="auth-title">{{ title }}</h2>
      <p class="sub" id="auth-sub">{{ subtitle }}</p>

      <!-- Name (register only) -->
      <div v-if="mode === 'register'" class="form-group">
        <label>Name</label>
        <input v-model="name" type="text" placeholder="Your name" />
      </div>

      <!-- Email -->
      <div v-if="mode !== 'reset' && mode !== 'otp'" class="form-group">
        <label>Email</label>
        <input v-model="email" type="email" placeholder="you@example.com" @keydown.enter="submit" />
      </div>

      <!-- Password -->
      <div v-if="mode === 'login' || mode === 'register' || mode === 'reset'" class="form-group" id="password-group">
        <label id="password-label">{{ mode === 'reset' ? 'New Password' : 'Password' }}</label>
        <input v-model="password" type="password" placeholder="••••••••" @keydown.enter="submit" />
      </div>

      <!-- Confirm password (reset only) -->
      <div v-if="mode === 'reset'" class="form-group">
        <label>Confirm Password</label>
        <input v-model="confirmPassword" type="password" placeholder="••••••••" @keydown.enter="submit" />
      </div>

      <!-- Forgot link (login only) -->
      <div v-if="mode === 'login'" class="forgot-link">
        <a @click="mode = 'forgot'">Forgot password?</a>
      </div>

      <!-- OTP input -->
      <div v-if="mode === 'otp'" class="form-group">
        <label>6-digit code</label>
        <input v-model="otp" type="text" maxlength="6" placeholder="123456" @keydown.enter="submit" />
      </div>

      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
      <p v-if="okMsg" class="login-ok">{{ okMsg }}</p>

      <button class="login-btn" :disabled="loading" @click="submit">
        {{ btnLabel }}
      </button>

      <!-- Resend OTP -->
      <div v-if="mode === 'otp'" style="text-align:center;margin-top:12px;font-size:13px;color:var(--muted)">
        Didn't get a code? <a style="color:var(--primary);cursor:pointer" @click="doResendOtp">Resend</a>
      </div>

      <!-- Switch between login / register / forgot -->
      <div v-if="mode !== 'reset' && mode !== 'otp'" class="login-switch">
        <template v-if="mode === 'login'">
          Don't have an account? <a @click="mode = 'register'">Sign up</a>
        </template>
        <template v-else-if="mode === 'register'">
          Already have an account? <a @click="mode = 'login'">Sign in</a>
        </template>
        <template v-else-if="mode === 'forgot'">
          Remember your password? <a @click="mode = 'login'">Sign in</a>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  authLogin, authRegister, authResetPassword,
  authUpdatePassword, authVerifyOtp, authResendOtp,
} from '../api'

type Mode = 'login' | 'register' | 'forgot' | 'otp' | 'reset'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const mode = ref<Mode>('login')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const name = ref('')
const otp = ref('')
const otpEmail = ref('')
const recoveryToken = ref<string | null>(null)
const loading = ref(false)
const errorMsg = ref('')
const okMsg = ref('')

const title = computed(() => ({
  login: 'Welcome back',
  register: 'Create account',
  forgot: 'Reset password',
  otp: 'Check your email',
  reset: 'Set new password',
}[mode.value]))

const subtitle = computed(() => ({
  login: 'Sign in to your account',
  register: 'Start your free account',
  forgot: "Enter your email and we'll send a reset link.",
  otp: `We sent a 6-digit code to ${otpEmail.value}`,
  reset: 'Enter your new password below.',
}[mode.value]))

const btnLabel = computed(() => {
  if (loading.value) return { login: 'Signing in…', register: 'Creating…', forgot: 'Sending…', otp: 'Verifying…', reset: 'Updating…' }[mode.value]
  return { login: 'Sign in', register: 'Create account', forgot: 'Send reset link', otp: 'Verify', reset: 'Update password' }[mode.value]
})

onMounted(() => {
  // Handle password reset link: /dashboard/login#type=recovery&access_token=...
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ''))
  if (hash.get('type') === 'recovery' && hash.get('access_token')) {
    recoveryToken.value = hash.get('access_token')
    mode.value = 'reset'
    history.replaceState(null, '', '/dashboard/login')
    return
  }
  // Handle ?confirmed=1 from email confirmation redirect
  if (route.query.confirmed === '1') {
    okMsg.value = 'Email confirmed! You can now sign in.'
    history.replaceState(null, '', '/dashboard/login')
  }
})

function clearMessages() { errorMsg.value = ''; okMsg.value = '' }

async function submit() {
  clearMessages()
  loading.value = true
  try {
    if (mode.value === 'login') {
      if (!email.value || !password.value) { errorMsg.value = 'Email and password are required'; return }
      const res = await authLogin(email.value, password.value)
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(email.value)
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
      router.push(redirect)

    } else if (mode.value === 'register') {
      if (!email.value || !password.value) { errorMsg.value = 'Email and password are required'; return }
      const res = await authRegister(email.value, password.value, name.value || email.value)
      if (!res.data.access_token) {
        otpEmail.value = email.value
        mode.value = 'otp'
        return
      }
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(email.value)
      router.push('/')

    } else if (mode.value === 'forgot') {
      if (!email.value) { errorMsg.value = 'Email is required'; return }
      await authResetPassword(email.value)
      okMsg.value = 'Reset link sent! Check your inbox.'

    } else if (mode.value === 'otp') {
      if (otp.value.length !== 6) { errorMsg.value = 'Enter the 6-digit code from your email'; return }
      const res = await authVerifyOtp(otpEmail.value, otp.value)
      authStore.setTokens(res.data.access_token, res.data.refresh_token)
      authStore.setEmail(otpEmail.value)
      router.push('/')

    } else if (mode.value === 'reset') {
      if (!password.value) { errorMsg.value = 'Password is required'; return }
      if (password.value !== confirmPassword.value) { errorMsg.value = 'Passwords do not match'; return }
      if (password.value.length < 6) { errorMsg.value = 'Password must be at least 6 characters'; return }
      await authUpdatePassword(recoveryToken.value!, password.value)
      okMsg.value = 'Password updated! Signing you in…'
      authStore.setTokens(recoveryToken.value!, null)
      setTimeout(() => router.push('/'), 1500)
    }
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    errorMsg.value = msg ?? 'Something went wrong'
  } finally {
    loading.value = false
  }
}

async function doResendOtp() {
  clearMessages()
  try {
    await authResendOtp(otpEmail.value)
    okMsg.value = 'Code resent! Check your inbox.'
  } catch {
    errorMsg.value = 'Failed to resend code'
  }
}
</script>
