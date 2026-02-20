import io
import os
import subprocess
import tempfile

from .excel_service import generate_adjustment_excel


def convert_excel_to_pdf(excel_buffer):
    """
    LibreOfficeを使用してExcelバッファをPDFバッファに変換する。
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        excel_path = os.path.join(tmp_dir, 'temp.xlsx')
        with open(excel_path, 'wb') as f:
            f.write(excel_buffer.read())

        # LibreOfficeによる変換 (headlessモード)
        commands = ['libreoffice', 'soffice']
        success = False
        last_error = ''

        for cmd in commands:
            try:
                subprocess.run(
                    [cmd, '--headless', '--convert-to', 'pdf', '--outdir', tmp_dir, excel_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                success = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                last_error = str(e)
                if isinstance(e, subprocess.CalledProcessError):
                    last_error += f'\nStderr: {e.stderr}'
                continue

        if not success:
            raise RuntimeError(f'PDF conversion failed. Ensure LibreOffice is installed. Error: {last_error}')

        pdf_path = os.path.join(tmp_dir, 'temp.pdf')
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f'Conversion failed: PDF file not created at {pdf_path}')

        with open(pdf_path, 'rb') as f:
            pdf_buffer = io.BytesIO(f.read())

        pdf_buffer.seek(0)
        return pdf_buffer


def generate_adjustment_pdf(data, member=None):
    """
    データをExcelに転記し、それをPDFに変換する (Single Source of Truth 方式)。
    """
    excel_buffer = generate_adjustment_excel(data, member, for_pdf=True)
    return convert_excel_to_pdf(excel_buffer)
