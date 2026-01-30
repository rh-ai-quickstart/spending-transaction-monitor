"""Model storage task for Alert Recommender Pipeline."""

from kfp import dsl
from kfp.dsl import Input, Output, Model, Artifact

from .constants import BASE_IMAGE


@dsl.component(base_image=BASE_IMAGE)
def save_model(input_model: Input[Model], output_artifact: Output[Artifact]):
    """
    Save the trained model to MinIO and prepare for deployment.
    
    This task:
    1. Loads the trained model from the training task
    2. Saves model components using joblib (Python version independent)
    3. Creates the MLServer model implementation file
    4. Uploads all artifacts to MinIO
    5. Creates model-settings.json for MLServer
    
    Inputs:
        input_model: Model from train_model containing model.pkl
    
    Outputs:
        output_artifact: Artifact containing model.joblib, model.py, vars.json
    """
    import os
    import json
    import pickle
    import joblib
    from datetime import datetime
    import boto3
    from botocore.client import Config
    
    # MLServer model code - must be embedded as string for KFP serialization
    model_impl_code = '''"""Custom MLServer model for Alert Recommender."""

import joblib
import numpy as np
from mlserver import MLModel
from mlserver.codecs import NumpyCodec
from mlserver.types import InferenceRequest, InferenceResponse, ResponseOutput


class AlertRecommenderModel(MLModel):
    """Custom MLServer model that loads our model components."""
    
    async def load(self) -> bool:
        """Load the model components from the joblib file."""
        model_uri = self.settings.parameters.uri
        self._components = joblib.load(model_uri)
        
        self._scaler = self._components['scaler']
        self._knn_model = self._components['knn_model']
        self._alert_labels = self._components['alert_labels']
        self._alert_types = self._components['alert_types']
        self._threshold = self._components['threshold']
        
        self.ready = True
        return self.ready
    
    async def predict(self, payload: InferenceRequest) -> InferenceResponse:
        """Make predictions using the loaded model."""
        # Decode input
        input_data = None
        for inp in payload.inputs:
            input_data = NumpyCodec.decode_input(inp)
            break
        
        if input_data is None:
            raise ValueError("No input data provided")
        
        # Scale the input
        X_scaled = self._scaler.transform(input_data)
        
        # Get nearest neighbors
        k_neighbors = min(5, len(self._alert_labels))
        distances, indices = self._knn_model.kneighbors(X_scaled, n_neighbors=k_neighbors)
        
        # Generate recommendations
        all_recommendations = []
        for idx_list in indices:
            similar_labels = self._alert_labels[idx_list]
            probabilities = similar_labels.mean(axis=0)
            
            recommendations = []
            for i, alert_type in enumerate(self._alert_types):
                if probabilities[i] >= self._threshold:
                    recommendations.append({
                        "alert_type": alert_type,
                        "probability": float(probabilities[i]),
                        "confidence": "high" if probabilities[i] >= 0.7 else "medium"
                    })
            
            all_recommendations.append(recommendations)
        
        # Encode output
        output_data = np.array(all_recommendations, dtype=object)
        
        return InferenceResponse(
            model_name=self.name,
            outputs=[
                ResponseOutput(
                    name="predictions",
                    shape=list(output_data.shape),
                    datatype="BYTES",
                    data=[str(r) for r in all_recommendations]
                )
            ]
        )
'''
    
    namespace = os.getenv('NAMESPACE', 'spending-transaction-monitor')
    bucket_name = os.getenv('BUCKET_NAME', 'models')
    minio_endpoint = os.getenv('MINIO_ENDPOINT', f'http://minio-service.{namespace}.svc.cluster.local:9000')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY', 'minio')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY', 'minio123')
    threshold = float(os.getenv('THRESHOLD', '0.4'))
    
    model_version = datetime.now().strftime("%y-%m-%d-%H%M%S")
    model_name = os.getenv('MODEL_NAME', 'alert-recommender')
    
    print(f"Model: {model_name}")
    print(f"Version: {model_version}")
    
    s3_client = boto3.client(
        's3',
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    
    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Created bucket: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e) or 'BucketAlreadyExists' in str(e):
            print(f"Bucket already exists: {bucket_name}")
        else:
            print(f"Note: {e}")
    
    model_path = os.path.join(input_model.path, 'model.pkl')
    with open(model_path, 'rb') as f:
        model_artifacts = pickle.load(f)
    
    print(f"Model artifacts loaded: {list(model_artifacts.keys())}")
    
    os.makedirs(output_artifact.path, exist_ok=True)
    
    model_components = {
        'scaler': model_artifacts['scaler'],
        'knn_model': model_artifacts['knn_model'],
        'alert_labels': model_artifacts['alert_labels'],
        'alert_types': model_artifacts['alert_types'],
        'threshold': threshold
    }
    
    pipeline_path = os.path.join(output_artifact.path, 'model.joblib')
    joblib.dump(model_components, pipeline_path, protocol=4)
    
    print(f"Model components saved: {os.path.getsize(pipeline_path) / 1024:.2f} KB")
    
    impl_path = os.path.join(output_artifact.path, 'model.py')
    with open(impl_path, 'w') as f:
        f.write(model_impl_code)
    
    s3_model_path = f'{model_name}/'
    
    model_key = f'{s3_model_path}model.joblib'
    print(f"Uploading model to s3://{bucket_name}/{model_key}")
    s3_client.upload_file(pipeline_path, bucket_name, model_key)
    
    impl_key = f'{s3_model_path}model.py'
    print(f"Uploading implementation to s3://{bucket_name}/{impl_key}")
    s3_client.upload_file(impl_path, bucket_name, impl_key)
    
    model_settings = {
        "name": model_name,
        "implementation": "model.AlertRecommenderModel",
        "parameters": {
            "uri": "/mnt/models/model.joblib"
        }
    }
    
    settings_key = f'{s3_model_path}model-settings.json'
    s3_client.put_object(
        Bucket=bucket_name,
        Key=settings_key,
        Body=json.dumps(model_settings, indent=2)
    )
    print(f"Uploaded model-settings.json")
    
    vars_data = {
        'model_version': model_version,
        'model_name': model_name,
        's3_bucket': bucket_name,
        's3_model_path': s3_model_path,
        'minio_endpoint': minio_endpoint
    }
    
    with open(os.path.join(output_artifact.path, 'vars.json'), 'w') as f:
        json.dump(vars_data, f, indent=2)
    
    print(f"Model save complete!")
    print(f"Model uploaded to: s3://{bucket_name}/{s3_model_path}")
