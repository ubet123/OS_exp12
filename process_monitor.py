import psutil
import time
import json
from datetime import datetime
from win10toast import ToastNotifier
import winsound
import threading

class AdvancedProcessMonitor:
    def __init__(self, alert_threshold=5, check_interval=5, cooldown_period=30):
        self.alert_threshold = alert_threshold
        self.check_interval = check_interval
        self.cooldown_period = cooldown_period
        self.alerts_log = []
        self.alerted_processes = {}
        self.toaster = ToastNotifier()
        self.notification_queue = []
        self.is_showing_notification = False
        
    def show_notification(self, title, message, duration=5):
        """Show Windows toast notification with sound - with queue support"""
        try:
            # Play alert sound immediately
            winsound.Beep(1000, 300)
            
            # Add to queue and process
            self.notification_queue.append((title, message, duration))
            self.process_notification_queue()
            
        except Exception as e:
            print(f"Notification failed: {e}")
    
    def process_notification_queue(self):
        """Process notifications one by one with delays"""
        if self.is_showing_notification or not self.notification_queue:
            return
            
        self.is_showing_notification = True
        title, message, duration = self.notification_queue.pop(0)
        
        try:
            # Show the notification
            self.toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=True
            )
        except Exception as e:
            print(f"Notification display failed: {e}")
        
        # Schedule next notification after a delay
        threading.Timer(duration + 1, self.notification_completed).start()
    
    def notification_completed(self):
        """Callback when notification is done"""
        self.is_showing_notification = False
        self.process_notification_queue()
    
    def show_consolidated_notification(self, alerts):
        """Show a single consolidated notification for multiple alerts"""
        if not alerts:
            return
            
        try:
            winsound.Beep(1000, 300)
            
            if len(alerts) == 1:
                # Single alert - show detailed notification
                alert = alerts[0]
                title = "🚨 High Memory Usage!"
                message = f"{alert['process_name']}\nUsing {alert['memory_usage_percent']:.1f}% RAM\n({alert['memory_usage_mb']:.0f} MB)"
            else:
                # Multiple alerts - show consolidated notification
                title = f"🚨 {len(alerts)} Processes High Memory!"
                message = f"Top offenders:\n"
                for alert in alerts[:3]:  # Show top 3 in notification
                    message += f"• {alert['process_name']}: {alert['memory_usage_percent']:.1f}%\n"
                if len(alerts) > 3:
                    message += f"• ... and {len(alerts) - 3} more"
            
            self.toaster.show_toast(
                title,
                message,
                duration=7,  # Longer duration for multiple alerts
                threaded=True
            )
            
        except Exception as e:
            print(f"Consolidated notification failed: {e}")
    
    def should_alert(self, process_key):
        """Check if we should alert for this process (cooldown period)"""
        current_time = time.time()
        if process_key in self.alerted_processes:
            last_alert = self.alerted_processes[process_key]
            if current_time - last_alert < self.cooldown_period:
                return False
        self.alerted_processes[process_key] = current_time
        return True
    
    def get_process_info(self):
        """Fetch information for all running processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'memory_info']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    def check_memory_alerts(self, processes):
        """Check if any process exceeds memory threshold"""
        alerts = []
        total_memory = psutil.virtual_memory()
        current_alerts = []
        
        for proc in processes:
            memory_usage = proc['memory_percent'] or 0
            if memory_usage > self.alert_threshold:
                process_key = f"{proc['pid']}_{proc['name']}"
                
                if self.should_alert(process_key):
                    # Calculate memory in MB
                    memory_mb = (proc['memory_info'].rss / 1024 / 1024) if proc['memory_info'] else 0
                    
                    alert_msg = f"Process {proc['name']} (PID: {proc['pid']}) using {memory_usage:.2f}% memory ({memory_mb:.1f} MB)"
                    alert_data = {
                        'timestamp': datetime.now().isoformat(),
                        'process_name': proc['name'],
                        'pid': proc['pid'],
                        'memory_usage_percent': memory_usage,
                        'memory_usage_mb': memory_mb,
                        'message': alert_msg
                    }
                    alerts.append(alert_data)
                    current_alerts.append(alert_data)
                    
                    print(f"🚨 {alert_msg}")
        
        # Show consolidated notification for all current alerts
        if current_alerts:
            self.show_consolidated_notification(current_alerts)
        
        # Alert for total system memory
        if total_memory.percent > 85:
            if self.should_alert("system_memory"):
                system_msg = f"System memory critically high: {total_memory.percent:.1f}%"
                self.show_notification("⚠️ System Critical", system_msg)
                print(f"⚠️  {system_msg}")
        
        return alerts
    
    def display_processes(self, processes, top_n=10):
        """Display top N processes by memory usage"""
        print("\n" + "="*70)
        print(f"{'PID':<8} {'Name':<20} {'Memory %':<12} {'Memory (MB)':<12} {'CPU %':<8}")
        print("="*70)
        
        # Sort by memory usage and show top N
        sorted_procs = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)
        
        for proc in sorted_procs[:top_n]:
            memory_pct = proc['memory_percent'] or 0
            cpu_pct = proc['cpu_percent'] or 0
            memory_mb = (proc['memory_info'].rss / 1024 / 1024) if proc['memory_info'] else 0
            print(f"{proc['pid']:<8} {proc['name'][:19]:<20} {memory_pct:<12.2f} {memory_mb:<12.0f} {cpu_pct:<8.2f}")
    
    def run_monitor(self, duration=300):
        """Main monitoring loop"""
        print(f"🚀 Starting Advanced Process Monitor")
        print(f"📊 Alert Threshold: {self.alert_threshold}% | Check Interval: {self.check_interval}s")
        print(f"⏱️  Monitoring for {duration} seconds...")
        print("Press Ctrl+C to stop early\n")
        
        # Show startup notification
        self.show_notification(
            "Process Monitor Started", 
            f"Monitoring active\nThreshold: {self.alert_threshold}%"
        )
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                processes = self.get_process_info()
                self.display_processes(processes)
                alerts = self.check_memory_alerts(processes)
                self.alerts_log.extend(alerts)
                
                memory = psutil.virtual_memory()
                print(f"\n📊 System: {memory.percent:.1f}% RAM used | {len(processes)} processes")
                print(f"⏰ Next check in {self.check_interval} seconds...\n")
                
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            self.show_notification("Process Monitor", "Monitoring stopped")
        
        self.generate_report()
    
    def generate_report(self):
        """Generate a summary report"""
        print("\n" + "="*60)
        print("📈 MONITORING REPORT")
        print("="*60)
        print(f"Total alerts triggered: {len(self.alerts_log)}")
        
        if self.alerts_log:
            print("\nRecent Alerts:")
            for alert in self.alerts_log[-5:]:
                print(f"  ⚠️  {alert['message']}")
        
        with open('memory_alerts.json', 'w') as f:
            json.dump(self.alerts_log, f, indent=2)
        print(f"\n📄 Full alert log saved to 'memory_alerts.json'")

# Run the enhanced monitor
if __name__ == "__main__":
    monitor = AdvancedProcessMonitor(
        alert_threshold=2.0,      # Alert if process uses >2% of total RAM
        check_interval=5,       # Check every 5 seconds
        cooldown_period=30      # Don't spam alerts for same process within 30 seconds
    )
    monitor.run_monitor(duration=300)  # Run for 5 minutes