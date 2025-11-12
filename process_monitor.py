import psutil
import time
import json
from datetime import datetime
from win10toast import ToastNotifier
import winsound

class AdvancedProcessMonitor:
    def __init__(self, alert_threshold=5, check_interval=5, cooldown_period=30):
        self.alert_threshold = alert_threshold
        self.check_interval = check_interval
        self.cooldown_period = cooldown_period  # Don't alert for same process within 30 seconds
        self.alerts_log = []
        self.alerted_processes = {}  # {process_key: last_alert_time}
        self.toaster = ToastNotifier()
        
    def show_notification(self, title, message, duration=5):
        """Show Windows toast notification with sound"""
        try:
            # Play alert sound
            winsound.Beep(1000, 300)
            
            # Show notification
            self.toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=True
            )
        except Exception as e:
            print(f"Notification failed: {e}")
    
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
        
        for proc in processes:
            memory_usage = proc['memory_percent'] or 0
            if memory_usage > self.alert_threshold:
                process_key = f"{proc['pid']}_{proc['name']}"
                
                if self.should_alert(process_key):
                    # Calculate memory in MB
                    memory_mb = (proc['memory_info'].rss / 1024 / 1024) if proc['memory_info'] else 0
                    
                    alert_msg = f"Process {proc['name']} (PID: {proc['pid']}) using {memory_usage:.2f}% memory ({memory_mb:.1f} MB)"
                    alerts.append({
                        'timestamp': datetime.now().isoformat(),
                        'process_name': proc['name'],
                        'pid': proc['pid'],
                        'memory_usage_percent': memory_usage,
                        'memory_usage_mb': memory_mb,
                        'message': alert_msg
                    })
                    
                    # Show desktop notification
                    notification_title = "🚨 High Memory Usage!"
                    notification_msg = f"{proc['name']}\nUsing {memory_usage:.1f}% RAM\n({memory_mb:.0f} MB)"
                    self.show_notification(notification_title, notification_msg)
                    
                    print(f"🚨 {alert_msg}")
        
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
        check_interval=10,       # Check every 10 seconds
        cooldown_period=30      # Don't spam alerts for same process within 30 seconds
    )
    monitor.run_monitor(duration=300)  # Run for 5 minutes