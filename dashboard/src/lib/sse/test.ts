/**
 * SSE Integration Test Script
 * 
 * This script can be used to test SSE functionality in the browser console
 * or as part of integration tests.
 */

import { sseManager } from './manager'
import type { SkaldEvent, TaskEvent } from '../../types'

/**
 * Test SSE connection and event handling
 */
export function testSSEIntegration() {
  console.log('🧪 Starting SSE Integration Test...')
  
  // Test connection
  console.log('📡 Testing connection...')
  sseManager.connect()
  
  setTimeout(() => {
    const isConnected = sseManager.isConnected()
    const lastError = sseManager.getLastError()
    
    console.log(`Connection Status: ${isConnected ? '✅ Connected' : '❌ Disconnected'}`)
    if (lastError) {
      console.log(`Last Error: ${lastError.message}`)
    }
  }, 2000)
  
  // Test Skald event subscription
  console.log('👥 Testing Skald event subscription...')
  const testSkaldId = 'test-skald-001'
  let skaldEventCount = 0
  
  const unsubscribeSkald = sseManager.subscribeToSkald(testSkaldId, (event: SkaldEvent) => {
    skaldEventCount++
    console.log(`📨 Skald Event #${skaldEventCount}:`, event)
  })
  
  // Test Task event subscription
  console.log('📋 Testing Task event subscription...')
  const testTaskId = 'test-task-001'
  let taskEventCount = 0
  
  const unsubscribeTask = sseManager.subscribeToTask(testTaskId, (event: TaskEvent) => {
    taskEventCount++
    console.log(`📨 Task Event #${taskEventCount}:`, event)
  })
  
  // Test connection state subscription
  console.log('🔌 Testing connection state subscription...')
  const unsubscribeConnection = sseManager.subscribeToConnection((connected: boolean) => {
    console.log(`🔌 Connection State Changed: ${connected ? 'Connected' : 'Disconnected'}`)
  })
  
  // Start mock events in development
  if (import.meta.env.DEV) {
    console.log('🎭 Starting mock events for testing...')
    sseManager.startMockEvents()
  }
  
  // Cleanup function
  const cleanup = () => {
    console.log('🧹 Cleaning up test subscriptions...')
    unsubscribeSkald()
    unsubscribeTask()
    unsubscribeConnection()
    sseManager.disconnect()
    console.log('✅ Test cleanup completed')
  }
  
  // Auto cleanup after 30 seconds
  setTimeout(() => {
    console.log('⏰ Auto cleanup after 30 seconds...')
    cleanup()
  }, 30000)
  
  console.log('🧪 SSE Integration Test started. Check console for events.')
  console.log('💡 Call cleanup() to stop the test early.')
  
  // Return cleanup function for manual cleanup
  return cleanup
}

/**
 * Test SSE reconnection behavior
 */
export function testSSEReconnection() {
  console.log('🔄 Testing SSE reconnection...')
  
  sseManager.connect()
  
  // Simulate connection loss after 5 seconds
  setTimeout(() => {
    console.log('💥 Simulating connection loss...')
    sseManager.disconnect()
    
    // Attempt reconnection after 2 seconds
    setTimeout(() => {
      console.log('🔄 Attempting reconnection...')
      sseManager.reconnect()
    }, 2000)
  }, 5000)
}

/**
 * Performance test for multiple subscriptions
 */
export function testSSEPerformance() {
  console.log('⚡ Testing SSE performance with multiple subscriptions...')
  
  const startTime = performance.now()
  const subscriptions: (() => void)[] = []
  
  // Create 100 skald subscriptions
  for (let i = 0; i < 100; i++) {
    const unsubscribe = sseManager.subscribeToSkald(`perf-skald-${i}`, (_event) => {
      // Minimal processing
    })
    subscriptions.push(unsubscribe)
  }
  
  // Create 100 task subscriptions
  for (let i = 0; i < 100; i++) {
    const unsubscribe = sseManager.subscribeToTask(`perf-task-${i}`, (_event) => {
      // Minimal processing
    })
    subscriptions.push(unsubscribe)
  }
  
  const subscriptionTime = performance.now() - startTime
  console.log(`📊 Created 200 subscriptions in ${subscriptionTime.toFixed(2)}ms`)
  
  // Test cleanup performance
  const cleanupStartTime = performance.now()
  subscriptions.forEach(unsubscribe => unsubscribe())
  const cleanupTime = performance.now() - cleanupStartTime
  
  console.log(`🧹 Cleaned up 200 subscriptions in ${cleanupTime.toFixed(2)}ms`)
  console.log('✅ Performance test completed')
}

// Export for browser console usage
if (typeof window !== 'undefined') {
  (window as any).testSSE = {
    integration: testSSEIntegration,
    reconnection: testSSEReconnection,
    performance: testSSEPerformance,
    manager: sseManager
  }
  
  console.log('🧪 SSE Test utilities available at window.testSSE')
  console.log('Usage:')
  console.log('  window.testSSE.integration() - Test basic integration')
  console.log('  window.testSSE.reconnection() - Test reconnection')
  console.log('  window.testSSE.performance() - Test performance')
  console.log('  window.testSSE.manager - Direct access to SSE manager')
}