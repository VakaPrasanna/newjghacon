
#!/usr/bin/env python3
"""
Enhanced Jenkins Declarative Pipeline -> GitHub Actions converter
Main entry point for the conversion tool with comprehensive error handling
"""

import sys
import yaml
from pathlib import Path
from converter import convert_jenkins_to_gha
from report_generator import generate_conversion_report


def main():
    if len(sys.argv) < 2:
        print("Enhanced Jenkins to GitHub Actions Converter")
        print("Usage: python main.py <path/to/Jenkinsfile> [output_directory]")
        print("  output_directory: Where to create .github/workflows/ci.yml and .github/actions/")
        print("\nFeatures:")
        print("  - Comprehensive Jenkins feature support")
        print("  - Stage-level post-action handling")
        print("  - Dashboard-style conversion reports")
        print("  - Automatic limitation detection")
        print("  - Manual conversion guidance")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    if not in_path.exists():
        print(f"Error: File not found: {in_path}")
        sys.exit(1)

    output_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    workflow_path = output_dir / ".github" / "workflows" / "ci.yml"
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "CONVERSION_REPORT.md"

    try:
        jenkins_text = in_path.read_text(encoding="utf-8")
        print(f"Converting {in_path} to GitHub Actions...")
        print("Analyzing pipeline structure and features...")
        
        # Perform the conversion
        gha, action_paths = convert_jenkins_to_gha(jenkins_text, output_dir)
        
        # Save workflow file with enhanced formatting
        print("Generating main workflow file...")
        with workflow_path.open("w", encoding="utf-8") as f:
            # Custom YAML representation for better formatting
            yaml_content = yaml.dump(gha, f, sort_keys=False, width=1000, default_flow_style=False, allow_unicode=True)
        
        print(f"✅ Main workflow saved to: {workflow_path}")
        
        # Generate and save comprehensive conversion report
        print("Generating conversion report...")
        report = generate_conversion_report(action_paths, jenkins_text)
        with report_path.open("w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"✅ Conversion report saved to: {report_path}")
        
        # Display summary of generated files
        print("\n📁 Generated files:")
        print(f"   - {workflow_path.relative_to(output_dir)}")
        print(f"   - {report_path.relative_to(output_dir)}")
        
        # List generated composite actions
        actions_dir = output_dir / ".github" / "actions"
        action_count = 0
        if actions_dir.exists():
            for action_dir in actions_dir.iterdir():
                if action_dir.is_dir():
                    action_file = action_dir / "action.yml"
                    if action_file.exists():
                        print(f"   - {action_file.relative_to(output_dir)}")
                        action_count += 1
        
        # Display conversion summary
        print(f"\n📊 Conversion Summary:")
        print(f"   - Stages converted: {len(action_paths)}")
        print(f"   - Composite actions created: {action_count}")
        
        # Check for manual conversion requirements
        manual_items = sum(len(a.get("manual_conversion_needed", [])) for a in action_paths)
        if manual_items > 0:
            print(f"   - Manual items requiring attention: {manual_items}")
            print("   ⚠️  Check CONVERSION_REPORT.md for detailed guidance")
        else:
            print("   ✅ No manual conversion required")
        
        # Check for approval environments
        approval_envs = [a for a in action_paths if a.get("approval_environment")]
        if approval_envs:
            print(f"   - Approval environments needed: {len(approval_envs)}")
            print("   📋 Configure these in GitHub repository settings")
        
        # Check for credentials
        all_credentials = set()
        for action in action_paths:
            all_credentials.update(action.get("credentials", []))
        
        if all_credentials:
            print(f"   - GitHub Secrets to configure: {len(all_credentials)}")
            print("   🔐 See report for complete secrets list")
        
        print(f"\n🎯 Next Steps:")
        print(f"   1. Review the comprehensive report: {report_path}")
        print(f"   2. Configure GitHub Secrets and Environments")
        print(f"   3. Test the workflow with a sample commit")
        print(f"   4. Address any manual conversion items")
        
        print(f"\n✨ Conversion completed successfully!")
        
    except ValueError as e:
        print(f"❌ Pipeline Parsing Error: {e}")
        print("\nThis usually means:")
        print("  - The file is not a valid Jenkins declarative pipeline")
        print("  - Required pipeline structure is missing")
        print("  - Syntax errors in the Jenkinsfile")
        print("\nPlease check your Jenkinsfile and try again.")
        sys.exit(1)
        
    except FileNotFoundError as e:
        print(f"❌ File Error: {e}")
        print("Please check the file path and try again.")
        sys.exit(1)
        
    except PermissionError as e:
        print(f"❌ Permission Error: {e}")
        print("Please check file permissions and try again.")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("\nDebug Information:")
        import traceback
        traceback.print_exc()
        print(f"\nPlease report this issue with:")
        print(f"  - The error message above")
        print(f"  - Your Jenkinsfile content (sanitized)")
        print(f"  - Python version: {sys.version}")
        sys.exit(1)


if __name__ == "__main__":
    main()

