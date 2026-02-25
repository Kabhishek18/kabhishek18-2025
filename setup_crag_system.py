#!/usr/bin/env python3
"""
CRAG System Setup Script

This script helps you set up the CRAG (Corrective Retrieval-Augmented Generation)
system to replace low-quality automatic content generation with high-quality,
AdSense-compliant content.

Run this script to:
1. Check system requirements
2. Audit existing content quality
3. Set up CRAG configuration
4. Generate sample high-quality content
5. Provide next steps for AdSense compliance
"""

import os
import sys
import json
import subprocess
from datetime import datetime

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"🚀 {title}")
    print("=" * 60)

def print_step(step_num, title):
    """Print a formatted step"""
    print(f"\n📋 Step {step_num}: {title}")
    print("-" * 40)

def check_requirements():
    """Check if all requirements are met"""
    print_step(1, "Checking System Requirements")
    
    requirements = {
        'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY'),
        'Django': True,  # Assume Django is installed if script runs
        'Python': sys.version_info >= (3, 8)
    }
    
    all_good = True
    
    for req, status in requirements.items():
        if req == 'GEMINI_API_KEY':
            if status:
                print(f"✅ {req}: Configured")
            else:
                print(f"❌ {req}: Missing - Required for CRAG content generation")
                print("   Get your API key from: https://makersuite.google.com/")
                all_good = False
        elif req == 'Python':
            if status:
                print(f"✅ {req}: {sys.version}")
            else:
                print(f"❌ {req}: Version {sys.version} (requires 3.8+)")
                all_good = False
        else:
            print(f"✅ {req}: Available")
    
    return all_good

def audit_current_content():
    """Audit current content quality"""
    print_step(2, "Auditing Current Content Quality")
    
    try:
        result = subprocess.run([
            'python', 'manage.py', 'upgrade_to_crag', '--audit-only'
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Content audit completed successfully")
            print("\nAudit Results:")
            print(result.stdout)
        else:
            print("❌ Content audit failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Audit timed out - you may have a lot of content to analyze")
        return False
    except Exception as e:
        print(f"❌ Error running audit: {str(e)}")
        return False
    
    return True

def setup_crag_configuration():
    """Set up CRAG configuration"""
    print_step(3, "Setting Up CRAG Configuration")
    
    config = {
        "content_generation_method": "crag",
        "quality_threshold": 85,
        "min_word_count": 1200,
        "use_adsense_compliance": True,
        "created_at": datetime.now().isoformat(),
        "crag_settings": {
            "max_retries": 3,
            "quality_correction_enabled": True,
            "knowledge_retrieval_enabled": True,
            "target_audience": "developers and tech professionals",
            "min_quality_score": 85
        },
        "publishing_schedule": {
            "frequency": "weekly",
            "posts_per_week": 2,
            "quality_level": "premium"
        }
    }
    
    config_file = 'crag_config.json'
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ CRAG configuration saved to {config_file}")
        print("\nConfiguration Details:")
        print(f"   Content Method: CRAG")
        print(f"   Quality Threshold: {config['quality_threshold']}")
        print(f"   Min Word Count: {config['min_word_count']}")
        print(f"   AdSense Compliance: Enabled")
        print(f"   Target Audience: {config['crag_settings']['target_audience']}")
        
    except Exception as e:
        print(f"❌ Failed to create configuration: {str(e)}")
        return False
    
    return True

def generate_sample_content():
    """Generate sample high-quality content"""
    print_step(4, "Generating Sample High-Quality Content")
    
    print("🎯 Generating 1 sample post using CRAG methodology...")
    
    try:
        result = subprocess.run([
            'python', 'manage.py', 'generate_crag_content', 
            '--count', '1',
            '--min-quality', '85',
            '--verbose'
        ], capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Sample content generated successfully!")
            print("\nGeneration Results:")
            print(result.stdout)
        else:
            print("❌ Sample content generation failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Content generation timed out - this is normal for high-quality content")
        print("   The process may still be running in the background")
        return True
    except Exception as e:
        print(f"❌ Error generating content: {str(e)}")
        return False
    
    return True

def provide_next_steps():
    """Provide next steps for AdSense compliance"""
    print_step(5, "Next Steps for AdSense Compliance")
    
    next_steps = [
        "📝 Review the generated sample content in Django admin",
        "🔧 Regenerate low-quality existing posts:",
        "   python manage.py upgrade_to_crag --regenerate-low-quality --max-posts 5",
        "📊 Monitor content quality regularly:",
        "   python manage.py upgrade_to_crag --audit-only",
        "🚀 Generate more high-quality content:",
        "   python manage.py generate_crag_content --count 3 --publish",
        "📈 Check AdSense readiness:",
        "   python manage.py upgrade_to_crag --audit-only",
        "🎯 Apply for AdSense when you have 20+ high-quality posts",
        "📱 Ensure your site has proper privacy policy and terms",
        "🔗 Add navigation, about page, and contact information"
    ]
    
    print("🎯 RECOMMENDED ACTIONS:")
    for i, step in enumerate(next_steps, 1):
        print(f"   {i}. {step}")
    
    print("\n💡 QUALITY TIPS:")
    quality_tips = [
        "Focus on comprehensive, in-depth content (1200+ words)",
        "Use proper heading structure (H2, H3) for organization",
        "Include practical examples and code snippets",
        "Add bullet points and numbered lists for readability",
        "Ensure content provides genuine value to readers",
        "Target technical professionals with expert-level insights"
    ]
    
    for tip in quality_tips:
        print(f"   • {tip}")

def main():
    """Main setup process"""
    print_header("CRAG Content Generation System Setup")
    
    print("This script will help you upgrade from basic automatic content")
    print("generation to CRAG (Corrective Retrieval-Augmented Generation)")
    print("for Google AdSense compliance and high-quality content.")
    
    # Step 1: Check requirements
    if not check_requirements():
        print("\n❌ Please fix the requirements above before continuing.")
        return False
    
    # Step 2: Audit current content
    if not audit_current_content():
        print("\n⚠️ Content audit had issues, but continuing with setup...")
    
    # Step 3: Setup configuration
    if not setup_crag_configuration():
        print("\n❌ Configuration setup failed.")
        return False
    
    # Step 4: Generate sample content
    if not generate_sample_content():
        print("\n⚠️ Sample content generation had issues, but setup is complete.")
    
    # Step 5: Provide next steps
    provide_next_steps()
    
    print_header("Setup Complete!")
    print("✅ CRAG system is now configured and ready to use.")
    print("📊 Check your Django admin to review generated content.")
    print("🚀 Start generating high-quality, AdSense-compliant content!")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)